// OMORI adapter. Staging, ownership and rollback follow the proven installer contract.
import Foundation
import AppKit
import Darwin

struct InstalledState: Codable {
    var schemaVersion = 1
    var gameRoot: String
    var locale: String
    var runtimeCode = "en"
    var catalog: String
    var originals: [String: String] // '-' means this path did not exist before installation.
    var owned: [String: String]
}
struct Operation: Codable { var path: String; var before: String; var after: String }
struct Journal: Codable { var schemaVersion = 1; var gameRoot: String; var previous: InstalledState?; var operations: [Operation] }
public final class InstallerCore {
    private let fm = FileManager.default
    public init() {}
    public static func checkPath(_ url: URL, below root: URL) throws {
        let base = root.standardizedFileURL.path
        let path = url.standardizedFileURL.path
        guard path == base || path.hasPrefix(base + "/") else { throw InstallerFailure("Path leaves the game folder.") }
        var cursor = url.standardizedFileURL
        while true {
            if let a = try? FileManager.default.attributesOfItem(atPath: cursor.path), a[.type] as? FileAttributeType == .typeSymbolicLink { throw InstallerFailure("A symbolic link blocks safe installation: \(cursor.lastPathComponent)") }
            if cursor.path == "/" { break }; cursor.deleteLastPathComponent()
        }
    }
    private func hash(_ p: URL) throws -> String {
        if !fm.fileExists(atPath: p.path) { return "-" }
        let a = try fm.attributesOfItem(atPath: p.path)
        guard a[.type] as? FileAttributeType == .typeRegular else { throw InstallerFailure("A file path is occupied by a folder or link: \(p.lastPathComponent)") }
        return digest(try Data(contentsOf: p))
    }
    private func save<T: Encodable>(_ value: T, to p: URL) throws { try JSONEncoder().encode(value).write(to: p, options: .atomic) }
    private func putBlob(_ data: Data, at store: URL) throws -> String {
        let h = digest(data);let p = store.appendingPathComponent(h)
        try Self.checkPath(p, below: store)
        if fm.fileExists(atPath: p.path) { guard try hash(p) == h else { throw InstallerFailure("A recovery backup is damaged.") } }
        else { try data.write(to: p, options: .atomic) }
        return h
    }
    private func blob(_ h: String, store: URL) throws -> Data {
        guard TranslationPackage.isHash(h) else { throw InstallerFailure("Invalid backup checksum.") }
        let p = store.appendingPathComponent(h);try Self.checkPath(p, below: store)
        let d = try Data(contentsOf: p);guard digest(d) == h else { throw InstallerFailure("A recovery backup is damaged.") };return d
    }
    private func setFile(_ target: URL, hash h: String, store: URL) throws {
        if h == "-" { if fm.fileExists(atPath: target.path) { try fm.removeItem(at: target) };return }
        let raw = try blob(h, store: store)
        try fm.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
        try raw.write(to: target, options: .atomic)
        guard try hash(target) == h else { throw InstallerFailure("File readback failed.") }
    }
    private func validateState(_ state: InstalledState, root: URL) throws {
        guard state.schemaVersion == 1, state.gameRoot == root.path, state.runtimeCode == "en" else { throw InstallerFailure("The install record belongs to another game folder.") }
        for (p,h) in state.originals { try TranslationPackage.validatePath(p);guard h == "-" || TranslationPackage.isHash(h) else { throw InstallerFailure("Invalid original backup record.") } }
        for (p,h) in state.owned { try TranslationPackage.validatePath(p);guard TranslationPackage.isHash(h), state.originals[p] != nil else { throw InstallerFailure("Invalid ownership record.") } }
    }
    private func recover(_ journalURL: URL, root: URL, store: URL, stateURL: URL) throws {
        guard fm.fileExists(atPath: journalURL.path) else { return }
        let j = try JSONDecoder().decode(Journal.self, from: Data(contentsOf: journalURL))
        guard j.schemaVersion == 1, j.gameRoot == root.path, Set(j.operations.map(\.path)).count == j.operations.count else { throw InstallerFailure("Invalid interrupted-install journal.") }
        if let old = j.previous { try validateState(old, root: root) }
        // Validate every boundary before restoring any file; unknown user edits are retained.
        for o in j.operations {
            try TranslationPackage.validatePath(o.path)
            guard (o.before == "-" || TranslationPackage.isHash(o.before)), (o.after == "-" || TranslationPackage.isHash(o.after)) else { throw InstallerFailure("Invalid recovery entry.") }
            let p = root.appendingPathComponent(o.path);try Self.checkPath(p, below: root)
            let current = try hash(p)
            guard current == o.before || current == o.after else { throw InstallerFailure("\(o.path) changed after an interrupted installation. Your file was preserved.") }
            if o.before != "-" { _ = try blob(o.before, store: store) }
        }
        for o in j.operations { try setFile(root.appendingPathComponent(o.path), hash: o.before, store: store) }
        if let previous = j.previous { try save(previous, to: stateURL) }
        else if fm.fileExists(atPath: stateURL.path) { try fm.removeItem(at: stateURL) }
        try fm.removeItem(at: journalURL)
    }
    public func activeLocale(in installation: GameInstallation) -> String? {
        let p = installation.resourceRoot.appendingPathComponent(".vnrevival-omori/state.json")
        guard let d = try? Data(contentsOf: p), let s = try? JSONDecoder().decode(InstalledState.self, from: d), s.gameRoot == installation.resourceRoot.standardizedFileURL.path else { return nil };return s.locale
    }
    public func apply(package: TranslationPackage, locale: String, installation: GameInstallation,
                      running: () -> Bool = { NSWorkspace.shared.runningApplications.contains { $0.bundleURL?.lastPathComponent.uppercased() == "OMORI.APP" } },
                      afterWrite: ((Int) throws -> Void)? = nil) throws {
        guard !running() else { throw InstallerFailure("Close OMORI before installing or changing the language.") }
        let root = installation.resourceRoot.standardizedFileURL
        try Self.checkPath(root, below: root)
        guard fm.fileExists(atPath: root.appendingPathComponent("data/System.KEL").path),
              let selected = package.catalog.locales.first(where: { $0.code == locale }) else { throw InstallerFailure("The selected game or language is unavailable.") }
        try package.verifyObjects()
        let metadata = root.appendingPathComponent(".vnrevival-omori")
        try Self.checkPath(metadata, below: root);try fm.createDirectory(at: metadata, withIntermediateDirectories: true)
        let lockURL = metadata.appendingPathComponent("install.lock")
        try Self.checkPath(lockURL, below: root)
        let fd = open(lockURL.path, O_CREAT | O_RDWR | O_NOFOLLOW, S_IRUSR | S_IWUSR)
        guard fd >= 0 else { throw InstallerFailure("Could not open the install lock.") };defer { close(fd) }
        guard flock(fd, LOCK_EX | LOCK_NB) == 0 else { throw InstallerFailure("Another OMORI installer is already working.") };defer { flock(fd, LOCK_UN) }
        let store = metadata.appendingPathComponent("backups")
        let stateURL = metadata.appendingPathComponent("state.json")
        let journalURL = metadata.appendingPathComponent("journal.json")
        for p in [store,stateURL,journalURL] { try Self.checkPath(p, below: root) }
        try fm.createDirectory(at: store, withIntermediateDirectories: true)
        try recover(journalURL, root: root, store: store, stateURL: stateURL)
        let cache = metadata.appendingPathComponent("packages/" + package.fingerprint)
        try Self.checkPath(cache, below: root)
        try fm.createDirectory(at: cache.appendingPathComponent("objects"), withIntermediateDirectories: true)
        for (key, record) in package.catalog.objects {
            let destination = cache.appendingPathComponent("objects/" + key)
            try Self.checkPath(destination, below: root)
            if fm.fileExists(atPath: destination.path) {
                guard try hash(destination) == record.sha256 else { throw InstallerFailure("A cached language package changed.") }
            } else { try Data(contentsOf: package.root.appendingPathComponent("objects/" + key)).write(to: destination, options: .atomic) }
        }
        let cachedCatalog = cache.appendingPathComponent("catalog.json")
        try Self.checkPath(cachedCatalog, below: root)
        if fm.fileExists(atPath: cachedCatalog.path) {
            guard try hash(cachedCatalog) == package.fingerprint else { throw InstallerFailure("The cached language catalog changed.") }
        } else { try Data(contentsOf: package.root.appendingPathComponent("catalog.json")).write(to: cachedCatalog, options: .atomic) }
        let previous = fm.fileExists(atPath: stateURL.path) ? try JSONDecoder().decode(InstalledState.self, from: Data(contentsOf: stateURL)) : nil
        if let previous { try validateState(previous, root: root) }
        var next = InstalledState(gameRoot: root.path, locale: locale, catalog: package.fingerprint, originals: previous?.originals ?? [:], owned: [:])
        let paths = Set(selected.files.keys).union(previous?.owned.keys.map { $0 } ?? [])
        var operations: [Operation] = []
        // Snapshot and stage the complete transaction before changing game assets.
        for path in paths.sorted() {
            let target = root.appendingPathComponent(path);try Self.checkPath(target, below: root)
            let current = try hash(target)
            if let owned = previous?.owned[path] {
                guard current == owned else { throw InstallerFailure("\(path) was changed by another mod or update. It was preserved.") }
            } else {
                let expected = next.originals[path] ?? package.catalog.originals[path] ?? "-"
                guard current == expected else { throw InstallerFailure("\(path) differs from the supported original game. Restore the file through Steam first; your file was preserved.") }
                next.originals[path] = current
            }
            if current != "-" { _ = try putBlob(Data(contentsOf: target), at: store) }
            let original = next.originals[path]!
            if original != "-", previous?.originals[path] != nil { _ = try blob(original, store: store) }
            let desired: String
            if let f = selected.files[path] {
                let bytes = try package.materialize(f);desired = try putBlob(bytes, at: store);next.owned[path] = desired
            } else { desired = original }
            if desired != current { operations.append(Operation(path: path, before: current, after: desired)) }
        }
        guard !running() else { throw InstallerFailure("Close OMORI before changing files.") }
        let journal = Journal(gameRoot: root.path, previous: previous, operations: operations)
        try save(journal, to: journalURL)
        // Journal remains on failure or process interruption. Next invocation rolls back
        // fully, including a state-file write completed just before the interruption.
        for (index, o) in operations.enumerated() {
            let p = root.appendingPathComponent(o.path);try Self.checkPath(p, below: root)
            guard try hash(p) == o.before else { throw InstallerFailure("A game file changed during installation; recovery is pending.") }
            try setFile(p, hash: o.after, store: store);try afterWrite?(index + 1)
        }
        try save(next, to: stateURL)
        try afterWrite?(0) // Exercise interruption after state commit, before journal removal.
        try fm.removeItem(at: journalURL)
    }
}
