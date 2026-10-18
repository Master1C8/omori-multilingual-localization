// Thin command-line access to the unchanged project's native installer adapter.
import Foundation
let args=CommandLine.arguments
if args.count != 5 { fatalError("Expected payload, catalog SHA256, native game app, locale") }
do {
 let p=try TranslationPackage(root:URL(fileURLWithPath:args[1]),expected:args[2])
 guard let g=GameDiscovery().resolve(URL(fileURLWithPath:args[3])) else {throw InstallerFailure("Native OMORI not found")}
 try InstallerCore().apply(package:p,locale:args[4],installation:g)
 guard InstallerCore().activeLocale(in:g)==args[4] else {throw InstallerFailure("Active locale readback mismatch")}
 print("APPLIED \(args[4]) \(p.fingerprint)")
}catch{fputs(error.localizedDescription+"\n",stderr);exit(1)}
