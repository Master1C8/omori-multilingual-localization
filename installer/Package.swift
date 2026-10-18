// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "OmoriInstaller", platforms: [.macOS(.v14)], products: [
    .executable(name: "OmoriInstaller", targets: ["OmoriInstaller"])
], targets: [
    .target(name: "OmoriCodec", linkerSettings: [.linkedLibrary("z")]),
    .target(name: "OmoriInstallerCore", dependencies: ["OmoriCodec"]),
    .executableTarget(name: "OmoriInstaller", dependencies: ["OmoriInstallerCore"]),
    .executableTarget(name: "OmoriInstallerChecks", dependencies: ["OmoriInstallerCore"], path: "Tests/OmoriInstallerChecks")
], swiftLanguageModes: [.v5])
