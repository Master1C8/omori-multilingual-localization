import Foundation
import OmoriInstallerCore
func check(_ value: @autoclosure () throws -> Bool, _ message: String) throws { if try !value() { throw InstallerFailure("TEST: " + message) } }
func rejects(_ message: String, _ action: () throws -> Void) throws {
    do { try action() } catch { try check(error.localizedDescription.contains(message), "wrong rejection: " + error.localizedDescription);return }
    throw InstallerFailure("TEST: expected rejection: " + message)
}
struct Fixture {
    let work: URL;let root: URL;let payload: URL;let package: TranslationPackage;let game: GameInstallation
    init(_ fixture: URL, _ directory: URL) throws {
        work = directory;root = work.appendingPathComponent("game");payload = work.appendingPathComponent("Payload")
        try FileManager.default.createDirectory(at: root.appendingPathComponent("data"), withIntermediateDirectories: true)
        try Data("official system".utf8).write(to: root.appendingPathComponent("data/System.KEL"))
        try Data("save remains unchanged".utf8).write(to: root.appendingPathComponent("file1.rpgsave"))
        try FileManager.default.copyItem(at: fixture, to: payload)
        package = try TranslationPackage(root: payload, expected: String(contentsOf: payload.appendingPathComponent("expected.sha256"), encoding: .utf8))
        game = GameInstallation(root: root, resourceRoot: root)
    }
    func apply(_ code: String, _ hook: ((Int) throws -> Void)? = nil) throws { try InstallerCore().apply(package: package, locale: code, installation: game, running: {false}, afterWrite: hook) }
    func bytes(_ p: String) throws -> Data { try Data(contentsOf: root.appendingPathComponent(p)) }
    func exists(_ p: String) -> Bool { FileManager.default.fileExists(atPath: root.appendingPathComponent(p).path) }
    func state() throws -> [String:Any] { try JSONSerialization.jsonObject(with: bytes(".vnrevival-omori/state.json")) as! [String:Any] }
}
do {
    if CommandLine.arguments.count == 5 && CommandLine.arguments[1] == "--verify-payload" {
        let p = try TranslationPackage(root: URL(fileURLWithPath: CommandLine.arguments[2]), expected: CommandLine.arguments[3])
        try p.verifyObjects()
        var files = 0
        for locale in p.catalog.locales { for f in locale.files.values { _ = try p.materialize(f); files += 1 } }
        let receipt: [String:Any] = ["status":"passed", "locales":p.catalog.locales.map(\.code), "deliveredFiles":files, "catalogSha256":p.fingerprint, "boundary":"actual Swift gzip and CommonCrypto reconstruction; no game writes"]
        try JSONSerialization.data(withJSONObject: receipt, options: .prettyPrinted).write(to: URL(fileURLWithPath: CommandLine.arguments[4]), options: .withoutOverwriting)
        print("PASS: reconstructed \(files) delivered native files");exit(0)
    }
    guard CommandLine.arguments.count == 3 else { throw InstallerFailure("Pass fixtures and a fresh output directory") }
    let fixtures = URL(fileURLWithPath: CommandLine.arguments[1]).resolvingSymlinksInPath()
    let output = URL(fileURLWithPath: CommandLine.arguments[2]).resolvingSymlinksInPath()
    try check(!FileManager.default.fileExists(atPath: output.path), "preserve existing test output")
    let f = try Fixture(fixtures, output.appendingPathComponent("switch"))
    try f.apply("es")
    try check(f.bytes("data/System.KEL") == f.package.materialize(f.package.catalog.locales[0].files["data/System.KEL"]!), "native gzip/CTR/hash materialization")
    try check(f.exists("fonts/Only-ES.ttf"), "first application installs locale-only file")
    try f.apply("fr");try check(!f.exists("fonts/Only-ES.ttf") && f.exists("fonts/Only-FR.ttf"), "old-only file removed")
    try check(InstallerCore().activeLocale(in: f.game) == "fr", "locale persisted")
    var changed = 0;try f.apply("fr") { if $0 > 0 { changed += 1 } };try check(changed == 0, "repeat has no asset writes")
    try check(f.bytes("file1.rpgsave") == Data("save remains unchanged".utf8), "save untouched")
    try f.apply("es")
    try rejects("interrupted") { try f.apply("fr") { if $0 == 1 { throw InstallerFailure("interrupted") } } }
    try check(f.exists(".vnrevival-omori/journal.json"), "mid-file journal retained")
    try f.apply("fr");try check(InstallerCore().activeLocale(in: f.game) == "fr", "continued from partial previous installation")
    try rejects("after state") { try f.apply("es") { if $0 == 0 { throw InstallerFailure("after state") } } }
    try check(InstallerCore().activeLocale(in: f.game) == "es", "state-write boundary reached")
    try f.apply("fr");try check(InstallerCore().activeLocale(in: f.game) == "fr" && !f.exists(".vnrevival-omori/journal.json"), "state-commit recovery")
    try rejects("unavailable") { try f.apply("xx") }
    try rejects("Close OMORI") { try InstallerCore().apply(package: f.package, locale: "es", installation: f.game, running: {true}) }
    try rejects("interrupted") { try f.apply("es") { if $0 == 1 { throw InstallerFailure("interrupted") } } }
    try Data("owner edit".utf8).write(to: f.root.appendingPathComponent("data/System.KEL"))
    try rejects("after an interrupted") { try f.apply("es") }
    try check(f.bytes("data/System.KEL") == Data("owner edit".utf8), "foreign edit after interruption preserved")
    let other = try Fixture(fixtures, output.appendingPathComponent("foreign"))
    try Data("another mod".utf8).write(to: other.root.appendingPathComponent("data/System.KEL"))
    try rejects("differs from the supported original") { try other.apply("es") }
    try check(other.bytes("data/System.KEL") == Data("another mod".utf8), "foreign original unchanged")
    let symlink = try Fixture(fixtures, output.appendingPathComponent("symlink"));let outside = output.appendingPathComponent("outside")
    try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: true)
    try FileManager.default.createSymbolicLink(at: symlink.root.appendingPathComponent("fonts"), withDestinationURL: outside)
    try rejects("symbolic link") { try symlink.apply("es") };try check(FileManager.default.contentsOfDirectory(atPath: outside.path).isEmpty, "no link traversal")
    let damaged = try Fixture(fixtures, output.appendingPathComponent("damaged"));let key = damaged.package.catalog.objects.keys.first!
    try Data("bad".utf8).write(to: damaged.payload.appendingPathComponent("objects/" + key))
    try rejects("damaged") { try damaged.apply("es") };try check(damaged.bytes("data/System.KEL") == Data("official system".utf8), "damaged payload before asset writes")
    try rejects("Unsafe") { try TranslationPackage.validatePath("data/../../save") }
    let result: [String:Any] = ["status":"passed", "groups":8, "boundary":"actual Swift filesystem, CommonCrypto CTR and gzip; fixture game, no runtime rendering"]
    try JSONSerialization.data(withJSONObject: result, options: .prettyPrinted).write(to: output.appendingPathComponent("result.json"));print("PASS: 8 macOS installer check groups")
} catch { fputs(error.localizedDescription + "\n", stderr);exit(1) }
