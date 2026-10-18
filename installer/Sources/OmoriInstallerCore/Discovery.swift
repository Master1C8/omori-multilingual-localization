// Adapted from StardewTranslationInstaller InstallerCore Steam discovery.
import Foundation
public struct GameInstallation: Equatable, Sendable {
    public let root: URL
    public let resourceRoot: URL
    public init(root: URL, resourceRoot: URL) { self.root = root; self.resourceRoot = resourceRoot }
}
public struct GameDiscovery {
    public init() {}
    public func resolve(_ selected: URL) -> GameInstallation? {
        let bases = [selected, selected.appendingPathComponent("OMORI.app")]
        for base in bases {
            let root = base.appendingPathComponent("Contents/Resources/app.nw")
            if FileManager.default.fileExists(atPath: root.appendingPathComponent("package.json").path),
               FileManager.default.fileExists(atPath: root.appendingPathComponent("data/System.KEL").path),
               let data = try? Data(contentsOf: root.appendingPathComponent("package.json")),
               let j = try? JSONSerialization.jsonObject(with: data) as? [String:Any],
               String(describing: j["name"] ?? "").uppercased().contains("OMORI") {
                return GameInstallation(root: base.standardizedFileURL, resourceRoot: root.standardizedFileURL)
            }
        }
        if selected.lastPathComponent == "app.nw", selected.path.contains("/OMORI.app/Contents/Resources/") {
            return resolve(selected.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent())
        }
        return nil
    }
    public func detect() -> GameInstallation? {
        let fm = FileManager.default
        let steam = fm.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Steam")
        var libraries = [steam]
        if let text = try? String(contentsOf: steam.appendingPathComponent("steamapps/libraryfolders.vdf"), encoding: .utf8),
           let re = try? NSRegularExpression(pattern: #""path"\s+"([^"]+)""#) {
            for match in re.matches(in: text, range: NSRange(text.startIndex..., in: text)) {
                if let range = Range(match.range(at: 1), in: text) { libraries.append(URL(fileURLWithPath: String(text[range]).replacingOccurrences(of: #"\\"#, with: #"\"#))) }
            }
        }
        var candidates = libraries.map { $0.appendingPathComponent("steamapps/common/OMORI/OMORI.app") }
        candidates += [URL(fileURLWithPath: "/Applications/OMORI.app"), fm.homeDirectoryForCurrentUser.appendingPathComponent("Applications/OMORI.app")]
        return candidates.compactMap(resolve).first
    }
}
