// Compare source YAML through the exact parser bundled with the installed game.
const fs=require('fs'),zlib=require('zlib'),path=require('path');
const yaml=require('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw/js/libs/js-yaml-master');
const reports=JSON.parse(fs.readFileSync('source/inventory-8879120-01/structured-assets.json'));
const rows=[];
for(const r of reports.filter(r=>!r.asset.endsWith('.KEL')&&!r.asset.endsWith('.AUBREY'))){
 const raw=zlib.gunzipSync(fs.readFileSync(path.join('source/inventory-8879120-01',r.snapshot))).toString();
 rows.push({asset:r.asset,native:yaml.safeLoad(raw)});
}
fs.writeFileSync('source/native-yaml-8879120-01/native-source.json',JSON.stringify(rows));
process.stdout.write(JSON.stringify({assets:rows.length,parser:'bundled js-yaml 3.11.0 safeLoad',gameBoot:false}));
