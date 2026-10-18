import Foundation
import CryptoKit
import OmoriCodec

public struct InstallerFailure: LocalizedError {
    public let text: String
    public init(_ text: String) { self.text = text }
    public var errorDescription: String? { text }
}
public func digest(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
public struct ObjectRecord: Codable { public let sha256: String; public let bytes: Int; public let unpackedBytes: Int }
public struct FileRecord: Codable { public let object: String; public let sha256: String; public let bytes: Int; public let iv: String }
public struct LocaleRecord: Codable { public let code: String; public let name: String; public let files: [String: FileRecord]; public let reviewStatus: String }
public struct Catalog: Codable {
    public let schemaVersion: Int; public let game: String; public let steamAppID: String; public let sourceBuild: String
    public let version: String; public let runtimeCode: String; public let originals: [String: String]
    public let objects: [String: ObjectRecord]; public let locales: [LocaleRecord]
}
public struct TranslationPackage {
    public let root: URL
    public let catalog: Catalog
    public let fingerprint: String
    public init(root: URL, expected: String) throws {
        self.root = root
        let raw = try Data(contentsOf: root.appendingPathComponent("catalog.json"))
        guard digest(raw) == expected else { throw InstallerFailure("The language package checksum did not match.") }
        catalog = try JSONDecoder().decode(Catalog.self, from: raw); fingerprint = expected
        guard catalog.schemaVersion == 1, catalog.game == "OMORI", catalog.steamAppID == "1150690", catalog.runtimeCode == "en",
              !catalog.locales.isEmpty, Set(catalog.locales.map(\.code)).count == catalog.locales.count else { throw InstallerFailure("Invalid OMORI package.") }
        for locale in catalog.locales { for (path, f) in locale.files {
            try Self.validatePath(path)
            guard Self.isHash(f.sha256), Self.isHash(f.object), catalog.objects[f.object] != nil,
                  let iv = Data(base64Encoded: f.iv), iv.count == 0 || iv.count == 16 else { throw InstallerFailure("Invalid package file: \(path)") }
        }}
    }
    public static func isHash(_ h: String) -> Bool { h.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil }
    public static func validatePath(_ p: String) throws {
        let parts = p.split(separator: "/", omittingEmptySubsequences: false)
        guard !p.contains("\\"), !p.contains(":"), !p.contains("\0"), !parts.contains(where: { $0.isEmpty || $0 == "." || $0 == ".." }),
              p == "index.html" || ["data", "js", "fonts"].contains(String(parts[0])) || p.hasPrefix("languages/en/") else { throw InstallerFailure("Unsafe package path: \(p)") }
    }
    public func verifyObjects() throws {
        for (key, o) in catalog.objects {
            guard Self.isHash(key), Self.isHash(o.sha256), o.bytes >= 0, o.unpackedBytes >= 0, o.unpackedBytes <= 64*1024*1024 else { throw InstallerFailure("Invalid object metadata.") }
            let file = root.appendingPathComponent("objects/" + key)
            try InstallerCore.checkPath(file, below: root)
            let data = try Data(contentsOf: file)
            guard data.count == o.bytes, digest(data) == o.sha256 else { throw InstallerFailure("A language file is damaged. Extract the installer again.") }
        }
    }
    public func materialize(_ f: FileRecord) throws -> Data {
        guard let o = catalog.objects[f.object] else { throw InstallerFailure("Missing language object.") }
        let compressed = try Data(contentsOf: root.appendingPathComponent("objects/" + f.object))
        guard digest(compressed) == o.sha256 else { throw InstallerFailure("Language checksum mismatch.") }
        var plain = Data(count: o.unpackedBytes)
        let status = plain.withUnsafeMutableBytes { dst in compressed.withUnsafeBytes { src in omori_gunzip(src.baseAddress, src.count, dst.baseAddress, dst.count) }}
        guard status == 0, digest(plain) == f.object else { throw InstallerFailure("Language decompression failed.") }
        var raw = plain
        if let iv = Data(base64Encoded: f.iv), !iv.isEmpty {
            var encrypted = Data(count: plain.count)
            let r = encrypted.withUnsafeMutableBytes { dst in plain.withUnsafeBytes { src in iv.withUnsafeBytes { v in omori_ctr(src.baseAddress, src.count, v.baseAddress, dst.baseAddress) }}}
            guard r == 0 else { throw InstallerFailure("Native resource encoding failed.") };raw = iv + encrypted
        }
        guard digest(raw) == f.sha256, raw.count == f.bytes else { throw InstallerFailure("Native file checksum mismatch.") };return raw
    }
}
