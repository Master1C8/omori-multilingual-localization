// Local source-text candidates only. Never translate, edit images or run OMORI.
import Foundation
import Vision

guard CommandLine.arguments.count == 3 else {
    fatalError("Expected media manifest and a NEW output JSONL path")
}
let manifestURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
guard !FileManager.default.fileExists(atPath: outputURL.path) else {
    fatalError("Preserve earlier OCR evidence; choose a new output")
}
let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: manifestURL)) as! [String: Any]
let assets = manifest["assets"] as! [[String: Any]]
FileManager.default.createFile(atPath: outputURL.path, contents: nil)
let output = try FileHandle(forWritingTo: outputURL)
var completed = 0
for asset in assets {
    guard asset["decodeStatus"] as? String == "passed", let path = asset["output"] as? String else { continue }
    autoreleasepool {
        var row: [String: Any] = ["asset": asset["asset"]!, "decodedRawSha256": asset["decodedRawSha256"]!,
                                 "status": "source-candidates-only", "manualReview": "pending",
                                 "ocr": "Apple Vision; accurate; en-US; language correction disabled"]
        do {
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesCPUOnly = ProcessInfo.processInfo.environment["OMORI_OCR_CPU_ONLY"] == "1"
            request.recognitionLanguages = ["en-US"]
            request.usesLanguageCorrection = false
            request.minimumTextHeight = 0.005
            let imageURL = manifestURL.deletingLastPathComponent().appendingPathComponent(path)
            try VNImageRequestHandler(url: imageURL).perform([request])
            row["candidates"] = (request.results ?? []).map { observation in
                ["rect": [observation.boundingBox.minX, observation.boundingBox.minY,
                           observation.boundingBox.width, observation.boundingBox.height],
                 "alternatives": observation.topCandidates(3).map { ["text": $0.string, "confidence": $0.confidence] }] as [String: Any]
            }
        } catch {
            row["status"] = "failed"
            row["error"] = error.localizedDescription
            row["errorDetails"] = String(reflecting: error)
        }
        do {
            let data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
            try output.write(contentsOf: data)
            try output.write(contentsOf: Data([10]))
        } catch { fatalError("Could not preserve OCR evidence: \(error)") }
    }
    completed += 1
    if completed % 100 == 0 { print("OCR candidates: \(completed) decoded source images processed") }
}
try output.close()
print("OCR completed: \(completed) decoded source images; every result still requires visual review")
