// Adapted from the proven StardewTranslationInstaller SwiftUI shell and AppState.
import SwiftUI
import AppKit
import OmoriInstallerCore

@main
struct OmoriInstallerApp: App {
    @StateObject private var state = AppState()
    var body: some Scene {
        WindowGroup("OMORI — VN Revival") { ContentView(state: state).frame(width: 510, height: 430) }
        .windowResizability(.contentSize)
    }
}
@MainActor final class AppState: ObservableObject {
    enum Phase { case preparing, choosing, installing, ready, failed }
    @Published var phase: Phase = .preparing
    @Published var message = "Finding OMORI…"
    @Published var selection = "ru"
    @Published var locales: [LocaleRecord] = []
    private var installation: GameInstallation?
    private var package: TranslationPackage?
    private let core = InstallerCore()
    private var started = false
    var title: String {
        switch phase { case .preparing: return "OMORI Languages"; case .choosing: return "Choose your language"; case .installing: return "Installing translation"; case .ready: return "Ready to play"; case .failed: return "Installation did not finish" }
    }
    func start() {
        guard !started else { return };started = true
        do {
            guard let resources = Bundle.main.resourceURL else { throw InstallerFailure("The installer resources are missing.") }
            let config = try JSONSerialization.jsonObject(with: Data(contentsOf: resources.appendingPathComponent("PackageConfig.json"))) as? [String:String]
            guard let hash = config?["catalogSha256"] else { throw InstallerFailure("The package configuration is missing.") }
            package = try TranslationPackage(root: resources.appendingPathComponent("Payload"), expected: hash)
            locales = package!.catalog.locales
            if let found = GameDiscovery().detect() { use(found) } else { phase = .choosing;message = "OMORI was not found. Choose the game folder." }
        } catch { fail(error) }
    }
    private func use(_ game: GameInstallation) {
        installation = game
        if let active = core.activeLocale(in: game), locales.contains(where: { $0.code == active }) { selection = active }
        phase = .choosing;message = "OMORI found. Choose a language to install."
    }
    func chooseGame() {
        let panel = NSOpenPanel();panel.title = "Choose OMORI";panel.message = "Choose OMORI.app or its Steam game folder."
        panel.canChooseDirectories = true;panel.canChooseFiles = true;panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        guard let found = GameDiscovery().resolve(url) else { return fail(InstallerFailure("This folder does not contain the native macOS version of OMORI.")) };use(found)
    }
    func install() {
        guard let installation, let package else { message = "Choose the OMORI game folder first.";return }
        phase = .installing;message = "Installing language packs and saving original files…"
        let code = selection
        Task {
            do {
                try await Task.detached(priority: .userInitiated) { try InstallerCore().apply(package: package, locale: code, installation: installation) }.value
                phase = .ready;message = "Translation installed. You can change the language here whenever OMORI is closed."
            } catch { fail(error) }
        }
    }
    func selectionChanged() {
        if phase == .ready { phase = .choosing; message = "Apply the selected language before launching OMORI." }
    }
    func launchGame() {
        guard phase == .ready else { return }
        if !NSWorkspace.shared.open(URL(string: "steam://rungameid/1150690")!) { fail(InstallerFailure("Open Steam and launch OMORI from your library.")) }
    }
    private func fail(_ error: Error) { phase = .failed;message = error.localizedDescription }
}
struct ContentView: View {
    @ObservedObject var state: AppState
    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: state.phase == .ready ? "checkmark.circle.fill" : "globe")
                .font(.system(size: 52, weight: .semibold)).foregroundStyle(state.phase == .ready ? Color.green : Color.accentColor)
            Text(state.title).font(.system(size: 25, weight: .bold, design: .rounded))
            ScrollView { Text(state.message).foregroundStyle(state.phase == .failed ? Color.red : Color.secondary).multilineTextAlignment(.center).textSelection(.enabled).frame(maxWidth: .infinity) }.frame(height: 70)
            Picker("Language", selection: $state.selection) { ForEach(state.locales, id: \.code) { Text($0.name).tag($0.code) } }
                .disabled(state.phase == .installing || state.phase == .preparing)
                .onChange(of: state.selection) { _, _ in state.selectionChanged() }
            if state.phase == .installing { ProgressView().progressViewStyle(.linear) }
            HStack {
                Button("Choose game…", action: state.chooseGame).disabled(state.phase == .installing)
                Spacer()
                Button(state.phase == .ready ? "Apply language" : "Install", action: state.install)
                    .buttonStyle(.borderedProminent).disabled(state.phase == .installing || state.locales.isEmpty)
            }
            if state.phase == .ready { Button("Launch game", action: state.launchGame).buttonStyle(.borderedProminent).controlSize(.large) }
            Text("OMORI · VN Revival").font(.caption).foregroundStyle(.tertiary)
        }.padding(30).task { state.start() }
    }
}
