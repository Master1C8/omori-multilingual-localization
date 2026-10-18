"""Source-bound native consumer compilation. This module never authors text."""
import copy
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from source_prepare import sha, strict_json
from text_resource_adapter import splice, exact_span_edit
from script_resource_adapter import at, put, recover_program, program_edit, parse_config
from source_name_variable_bindings import collect as name_bindings
from source_password_bindings import collect as password_bindings
import yaml

HERE = Path(__file__).resolve().parent
API = 'OmoriLocale'

def js(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def calls(ctx, source):
    run = subprocess.run(['node', '--expose-internals', str(HERE.parents[1]/'display_calls.cjs')],
                         input=source, text=True, capture_output=True)
    if run.returncode:
        raise ValueError('Consumer AST failed: ' + run.stderr[-900:])
    return strict_json(run.stdout)


def span(source, a, b, replacement, identity):
    return {'id': identity, 'span': [a, b], 'original': source.encode('utf-16-le')[2*a:2*b].decode('utf-16-le'),
            'replacement': replacement}


def replace(source, old, new, identity):
    if source.count(old) != 1:
        raise ValueError('Ambiguous source-bound consumer: ' + identity)
    start = len(source[:source.index(old)].encode('utf-16-le'))//2
    return span(source, start, start+len(old.encode('utf-16-le'))//2, new, identity)


def direct_edits(ctx, pairs, config):
    direct = defaultdict(list)
    originals = {}
    def source(asset):
        if asset not in originals:
            rec = ctx.known.get(asset)
            originals[asset] = recover_program(rec, ctx.original(rec['originalAsset'])[1]) if rec else ctx.original(asset)[0]
        return originals[asset]
    def edit(asset, old, new, label):
        direct[asset].append(replace(source(asset), old, new, label))
    consumers = strict_json((HERE/'consumers.json').read_bytes())['consumers']
    for row in consumers:
        asset, value = row['asset'], row['expression']
        if value.endswith('.name()'):
            target = API+'.name('+value[:-7]+')'
        elif value.endswith('.displayName()'):
            target = API+'.mapName('+value[:-14]+')'
        elif value.endswith('.name'):
            target = API+'.recordName('+value[:-5]+')'
        else:
            raise ValueError('Unknown typed consumer: '+value)
        if asset == 'js/plugins/Omori Save & Load.OMORI' and value == 'actor.name':
            target = API+'.savedActor(info)'
        item = span(source(asset), *row['span'], target, 'typed:'+str(row['span']))
        if item['original'] != value:
            raise ValueError('Consumer expression/source span changed')
        direct[asset].append(item)
    save = 'js/plugins/Omori Save & Load.OMORI'
    edit(save, 'this.contents.drawText(LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").file.format(id), loc_position[0], loc_position[1], 100, this.contents.fontSize);',
         'OmoriLocaleUI.drawFileHeader(this, LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").file.format(id), valid ? info : null, loc_position[0], loc_position[1], this.contents.fontSize);', 'file-header-layout')
    edit(save, 'this.contents.drawText(chap, loc_position[0], loc_position[1], this.contents.width, this.contents.fontSize);',
         '/* Chapter is drawn with the measured file heading above. */', 'file-chapter-layout')
    edit(save, 'this.contents.drawText(LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").level, loc_position[0], loc_position[1], 100, 24);\r\n    this.contents.drawText(actor.level, loc_position[0], loc_position[1], 70, 24, \'right\');',
         'OmoriLocaleUI.drawFileLevel(this, LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").level, actor.level, loc_position[1], 24);', 'file-level-layout')
    edit(save, 'this.contents.drawText(LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").playtime, 118, 55, 200, 24);\r\n    this.contents.drawText(info.playtime, loc_position[0], loc_position[1], 100, 24);',
         'OmoriLocaleUI.drawFilePair(this, LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").playtime, info.playtime, 55, 24);', 'file-playtime-layout')
    edit(save, 'this.contents.drawText(LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").location, 118, 80, 200, 24);\r\n    this.contents.drawText(info.location, 205, 80, 210, 24, \'right\');',
         'OmoriLocaleUI.drawFilePair(this, LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").location, OmoriLocale.savedLocation(info), 80, 24);', 'save-location-layout')
    cursor = 'Window_OmoriFileCommand.prototype.customCursorRectTextXOffset = function() { return 40; }'
    edit(save, cursor, cursor+'\r\nWindow_OmoriFileCommand.prototype.customCursorRectTextWidthOffset = function() { return -this.customCursorRectTextXOffset(); };', 'save-bounds')
    asset = 'js/plugins/Omori Title Screen.OMORI'
    anchor = '  this._commandHints.bitmap.drawInputIcon("ok", 0, paddingY);'
    layout = '''  let confirmPosition = LanguageManager.getMessageData("XX_BLUE.Scene_OmoriTitleScreen").commandHints_confirm_position;
  let cancelPosition = LanguageManager.getMessageData("XX_BLUE.Scene_OmoriTitleScreen").commandHints_cancel_position;
  let hintWidth = Math.ceil(Math.max(eval(confirmPosition[0]) + this._commandHints.bitmap.measureTextWidth(confirm),
    eval(cancelPosition[0]) + this._commandHints.bitmap.measureTextWidth(cancel), iconSize + 15 + this._commandHints.bitmap.measureTextWidth(confirm) + iconSize) + 4);
  this._commandHints.bitmap.resize(hintWidth, this._commandHints.bitmap.height);
  this._commandHints.setFrame(0, 0, hintWidth, this._commandHints.bitmap.height);
  this._commandHints.position.set(Graphics.boxWidth - hintWidth, 0);
'''
    edit(asset, anchor, layout+anchor, 'title-bounds')
    edit('js/plugins/YEP_StealSnatch.OMORI', 'name, icon);', '(item ? OmoriLocale.recordName(item) : name), icon);', 'steal-format')
    asset = 'js/rpg_windows.js'
    ast = calls(ctx, source(asset))
    owner = next(c for c in ast if c['type']=='FunctionAssignment' and c['owner']=='Window_Base.prototype.convertEscapeCharacters')
    for c in ast:
        if c['type']=='CallExpression' and c['callee']=='$gameVariables.value' and owner['span'][0]<=c['span'][0]<owner['span'][1]:
            direct[asset].append(span(source(asset), c['span'][0], c['span'][0]+len('$gameVariables.value'), 'OmoriLocale.variable', 'variable-escape'))
    edit('js/rpg_objects.js', 'TextManager.levelUp.format(this._name,', 'TextManager.levelUp.format(OmoriLocale.name(this),', 'level-name')
    for asset in ['js/rpg_managers.js', 'js/plugins/YEP_BattleEngineCore.OMORI']:
        edit(asset, '$gameTroop.enemyNames()', 'OmoriLocale.enemyNames()', 'enemy-names')
    asset = 'js/plugins/Omori Battle System.OMORI'
    short = [c for c in calls(ctx,source(asset)) if c['type']=='CallExpression' and c['callee']=='DataManager.itemShortName']
    if len(short)!=2 or any(c['args'][0]['source']!='item' for c in short):
        raise ValueError('Short-name consumer changed')
    for c in short:
        a,b = c['span']
        raw = span(source(asset),a,b,'','short')['original']
        direct[asset].append(span(source(asset),a,b,'OmoriLocale.displayField(item, '+raw+')','short-name'))
    edit('js/plugins/YIN - Minigame - Jukebox.OMORI', '$gameVariables.setValue(829, $dataItems[jukeboxCDs[i]].name)',
         'OmoriLocale.setRecordVariable(829, $dataItems[jukeboxCDs[i]])', 'jukebox-variable')
    # Extend the existing keyboard, rather than inheriting a Russian layout or changing identities.
    extra = config['keyboardExtra']
    if config.get('keyboardLayouts'):
        asset = 'js/plugins/Omori Name Input.OMORI'
        anchor = '    this._currentLayout = VirtualKeyboard[language][this._layoutType].map(l => l.split(" "))'
        edit(asset, anchor, anchor+'\r\n    if(language === "EN" && OmoriLocale.keyboardLayouts[this._layoutType]) this._currentLayout = OmoriLocale.keyboardLayouts[this._layoutType].map(row => row.slice());', 'locale-input-layout')
    elif extra:
        asset = 'js/plugins/Omori Name Input.OMORI'
        anchor = '    this._currentLayout = VirtualKeyboard[language][this._layoutType].map(l => l.split(" "))'
        edit(asset, anchor, anchor+'\r\n    if(language === "EN") this._currentLayout = this._currentLayout.concat(OmoriLocale.keyboardRows);', 'locale-input-glyphs')
    if config.get('textRenderer') in ('arabic-context-runs-v1','hebrew-context-runs-v1','devanagari-context-runs-v1','thai-clusters-v1'):
        arabic=config['textRenderer'] in ('arabic-context-runs-v1','hebrew-context-runs-v1')
        asset = 'js/plugins/TDS Text Effects.OMORI'
        edit(asset, 'var c = textState.text[textState.index];',
             'var c = textState._omoriRunText || textState.text[textState.index];', 'contextual-effect-run')
        edit(asset, 'var bitmap = new Bitmap(w, textState.height + 10);',
             'var bitmap = new Bitmap(w + 4, textState.height + 10);'+('\n  bitmap._omoriRtlRun = !!textState._omoriRunText;' if arabic else ''), 'contextual-effect-direction')
        if config['textRenderer']!='thai-clusters-v1':
            asset = 'js/plugins/Omori Name Input.OMORI'
            found = [c for c in calls(ctx,source(asset)) if c['type']=='FunctionAssignment' and c['owner']=='Window_OmoriNameInputName.prototype.refreshText']
            if len(found)!=1:raise ValueError('Contextual name-display source boundary changed')
            adapter=('OmoriLocaleHebrew' if config['textRenderer']=='hebrew-context-runs-v1' else 'OmoriLocaleArabic') if arabic else 'OmoriLocaleDevanagari'
            direct[asset].append(span(source(asset),*found[0]['span'],'function() { return '+adapter+'.refreshName(this); }','contextual-name-display'))
    # The native actor/save validator otherwise discards authored non-ASCII names on EN.
    asset = 'js/plugins/GTP_OmoriFixes.OMORI'
    old = 'if(!englishOnly.test(text)) {return false}'
    edit(asset, old, 'if(!englishOnly.test(text) && !OmoriLocale.validName(text)) {return false}', 'locale-name-validation')
    # Native pizza words are image identifiers; keep generation/grading and draw authored text.
    asset = 'js/plugins/YIN - Minigame - PizzaDelivery.OMORI'
    ast = calls(ctx,source(asset))
    for owner,target in [('Window_PizzaDeliveryNote.prototype.refresh','function (text) { return OmoriLocale.renderPizzaNote(this, text); }'),
                         ('Game_Interpreter.prototype.checkImages',"function () { ImageManager.loadPicture('PIZZA-Background'); }")]:
        found = [c for c in ast if c['type']=='FunctionAssignment' and c['owner']==owner]
        if len(found)!=1: raise ValueError('Pizza presentation consumer changed')
        direct[asset].append(span(source(asset),*found[0]['span'],target,'pizza:'+owner))
    asset = 'js/plugins/Custom Battle Action Text.OMORI'
    edit(asset,'function parseNoEffectEmotion(tname, em)','function parseNoEffectEmotion(tname, em, displayName, displayEmotion)','emotion-arguments')
    edit(asset,'let finalString = `${tname}', 'let finalString = `${displayName}', 'emotion-name')
    edit(asset,'${em}','${displayEmotion}','emotion-value')
    mapping = {tuple(u['spanUtf16']):u for u,e in pairs if u['asset']==asset and u['role']=='visible-display-mapping'}
    for c in calls(ctx, source(asset)):
        if c['type']=='CallExpression' and c['callee']=='parseNoEffectEmotion':
            value = c['args'][0]['source']
            if not value.endswith('.name()'): raise ValueError('Emotion name consumer changed')
            row = mapping.get(tuple(c['args'][1]['span']))
            emotion = 'OmoriLocale.label('+js(row['id'])+', '+c['args'][1]['source']+')' if row else c['args'][1]['source']
            direct[asset].append(span(source(asset),c['span'][1]-1,c['span'][1]-1,', OmoriLocale.name('+value[:-7]+'), '+emotion,'emotion-call'))
    asset = 'js/plugins/GTP_OmoriFixes.OMORI'
    ast = calls(ctx, source(asset))
    for u,e in pairs:
        if u['asset']!=asset or u['role']!='visible-display-mapping':continue
        c = next(c for c in ast if c['type']=='NewExpression' and c['callee']=='Error' and c['args'][0]['span']==u['spanUtf16'])
        a,b = c['span']
        direct[asset].append(span(source(asset),a,a,'OmoriLocale.error('+js(u['id'])+', ','error-open'))
        direct[asset].append(span(source(asset),b,b,')','error-close'))
    for asset in ['js/rpg_managers.js','js/plugins/YEP_CoreEngine.OMORI']:
        edit(asset,'e.name, e.message','e.name, OmoriLocale.errorMessage(e)','error-display')
    return direct, consumers


def compile_resources(ctx, pairs, mapping, config, font_probes):
    direct, consumers = direct_edits(ctx,pairs,config)
    originals, texts, results = {}, {}, {}
    fields, scripts = defaultdict(list), defaultdict(list)
    def load(asset):
        if asset not in originals:
            texts[asset],originals[asset]=ctx.original(asset)
            results[asset]=copy.deepcopy(originals[asset])
    for u,e in pairs:
        rec=ctx.known.get(u['asset']); asset=rec['originalAsset'] if rec else u['asset'];load(asset)
        if 'spanUtf16' in u:
            scripts[u['asset']].append((u,e))
        elif u['role']!='visible-display-mapping':
            path=tuple(u['path'])
            if 'span' in u or 'spanCodepoints' in u:
                fields[asset,path].append(exact_span_edit(u,e['target'],ctx.macros))
            else: put(results[asset],path,e['target'])
    core=[]; source_proofs=[]
    for source_asset in sorted(set(scripts)|set(direct)):
        rec=ctx.known.get(source_asset);asset=rec['originalAsset'] if rec else source_asset;load(asset)
        src=recover_program(rec,originals[asset]) if rec else texts[asset]
        edits=[program_edit(u,e,ctx.macros) for u,e in scripts[source_asset]]+direct[source_asset]
        dst=splice(src,edits,utf16=True)
        source_proofs.append({'asset':source_asset,'sourceSha256':sha(src.encode()),'compiledSha256':sha(dst.encode()),'consumerEdits':direct[source_asset]})
        if rec:
            if 'linePaths' in rec:
                lines=dst.splitlines(keepends=True)
                if len(lines)!=len(rec['linePaths']) or any(not x.endswith('\n') for x in lines):raise ValueError('Embedded physical line binding changed')
                for path,line in zip(rec['linePaths'],lines):put(results[asset],path,line[:-1])
            elif 'spanCodepoints' in rec:
                fields[asset,tuple(rec['parentPath'])].append({'id':source_asset,'span':rec['spanCodepoints'],'original':src,'replacement':dst})
            else: put(results[asset],rec['parentPath'],dst)
        elif source_asset.startswith('js/plugins/'):
            results[asset]=dst
        else:
            nontrivial=[e for e in edits if e['replacement']!=e['original']]
            covered=set()
            for owner in calls(ctx,src):
                if owner['type']!='FunctionAssignment':continue
                a,b=owner['span'];local=[]
                for i,e in enumerate(nontrivial):
                    if a<=e['span'][0] and e['span'][1]<=b:
                        local.append(dict(e,span=[e['span'][0]-a,e['span'][1]-a]));covered.add(i)
                if local: core.append({'asset':asset,'owner':owner['owner'],'source':owner['source'],'target':splice(owner['source'],local,utf16=True)})
            if covered!=set(range(len(nontrivial))):raise ValueError('Unwired protected core consumer')
    # Merge scalar note fragments and embedded programs against their one original parent.
    for (asset,path),edits in fields.items():put(results[asset],path,splice(at(originals[asset],path),edits))
    variables=[]; byid={u['id']:e for u,e in pairs}
    for row in mapping:
        rec=ctx.known.get(row['asset'])
        if not rec:continue
        asset=rec['originalAsset'];load(asset)
        path=rec['linePaths'][0][:-2] if 'linePaths' in rec else rec['parentPath'][:-2]
        command=at(results[asset],path)
        if 'linePaths' in rec:
            if command['code']!=355: raise ValueError('Chapter variable command changed')
            var_id=23
        else:
            if command['code']!=122 or command['parameters'][2:4]!=[0,4] or command['parameters'][0]!=command['parameters'][1]:raise ValueError('Direct variable identity changed')
            var_id=command['parameters'][0]
        variables.append({'asset':asset,'commandPath':path,'code':command['code'],'parameters':js(command['parameters']), 'labels':[{'variableId':var_id,'unitId':row['id']}]})
    variables.extend(name_bindings(ctx.root)['bindings'])
    password=password_bindings(ctx.root)['bindings']
    for binding in password:
        for label in binding['labels']:label['catalogTarget']=byid[label['catalogUnitId']]['target']
    variables.extend(password)
    # Bind to the actual compiled commands, whose display calls may have changed.
    for b in variables:
        load(b['asset']);cmd=at(results[b['asset']],b['commandPath'])
        if cmd['code']!=b['code']:raise ValueError('Compiled variable command code changed')
        b['parameters']=js(cmd['parameters'])
        if b.get('sourceCommands'):
            parent=at(results[b['asset']],b['commandPath'][:-1]);start=b['commandPath'][-1]
            b['sourceCommands']=parent[start:start+len(b['sourceCommands'])]
    # Duplicate command bindings are only legal when identical. Do not overwrite labels.
    unique={}
    for b in variables:
        key=(b['asset'],tuple(b['commandPath']))
        if key in unique and unique[key]!=b:raise ValueError('Conflicting variable consumers')
        unique[key]=b
    variables=list(unique.values())
    config_plugins=results['js/plugins.js']
    bootstrap=(HERE/'ui_layout.js').read_text()+'\n'+(HERE/'engine_display.js').read_text()+'\n'+(HERE/'pizza_note.js').read_text()+'\n'
    if config.get('textRenderer') == 'arabic-context-runs-v1':
        bootstrap+=(HERE/'arabic_joining.js').read_text()+'\n'+(HERE/'arabic_runs.js').read_text()+'\n'
    elif config.get('textRenderer') == 'hebrew-context-runs-v1':
        bootstrap+=(HERE/'arabic_runs.js').read_text()+'\n'
        bootstrap+='this.OmoriLocaleHebrew=this.OmoriLocaleArabic.create({scriptPattern:/[\\u0590-\\u05ff]/,marker:"_hebrewRunsInstalled",joining:false});\n'
    elif config.get('textRenderer') == 'devanagari-context-runs-v1':
        bootstrap+=(HERE/'devanagari_runs.js').read_text()+'\n'
    elif config.get('textRenderer') == 'thai-clusters-v1':
        bootstrap+=(HERE/'thai_clusters.js').read_text()+'\n'
    if config.get('textRenderer') in ('arabic-context-runs-v1','hebrew-context-runs-v1','devanagari-context-runs-v1'):
        bootstrap+=(HERE/'run_wave.js').read_text()+'\n'
    bootstrap+='(function(root){\n'
    bootstrap+='root.OmoriLocale = root.OmoriLocaleEngineDisplay.create('+js(mapping)+','+js(variables)+',root,[]);\n'
    bootstrap+='root.OmoriLocale.renderPizzaNote=root.OmoriLocalePizzaNote.render;\n'
    extra=list(config['keyboardExtra']); rows=[extra[i:i+13] for i in range(0,len(extra),13)]
    bootstrap+='root.OmoriLocale.keyboardRows='+js(rows)+';\n'
    bootstrap+='root.OmoriLocale.keyboardLayouts='+js(config.get('keyboardLayouts',{}))+';\n'
    allowed=set(config['keyboardExtra'])|set(''.join(e['target'] for u,e in pairs if u['asset']=='data/Actors.KEL' and u.get('path',[])[-1:] == ['name']))
    bootstrap+='var allowed='+js(''.join(sorted(allowed)))+';root.OmoriLocale.validName=function(text){return Array.from(text).every(function(c){return /^[\\x20-\\x7e☆]$/.test(c)||allowed.indexOf(c)>=0;});};\n'
    bootstrap+='function normalized(s){return s.replace(/\\r\\n?/g,"\\n").replace(/^function[ \\t]*\\(/,"function(");}\n'
    for row in core:
        bootstrap+='if(normalized('+row['owner']+'.toString())!==normalized('+js(row['source'])+'))throw new Error('+js('Locale core source mismatch: '+row['owner'])+');\n'+row['owner']+' = '+row['target']+';\n'
    bootstrap+='}(this));\n'
    install=(HERE/'font_ready.js').read_text()+'\n(function(root){root.OmoriLocale.install();root.OmoriLocaleFonts.install(root,'+js(font_probes)+');\n'
    if config.get('textRenderer') == 'arabic-context-runs-v1':install+='root.OmoriLocaleArabic.install(root);\n'
    elif config.get('textRenderer') == 'hebrew-context-runs-v1':install+='root.OmoriLocaleHebrew.install(root);\n'
    elif config.get('textRenderer') == 'devanagari-context-runs-v1':install+='root.OmoriLocaleDevanagari.install(root);\n'
    elif config.get('textRenderer') == 'thai-clusters-v1':install+='root.OmoriLocaleThai.install(root);\n'
    if config.get('textRenderer') in ('arabic-context-runs-v1','hebrew-context-runs-v1','devanagari-context-runs-v1'):
        install+='root.OmoriLocaleRunWave.install(root);\n'
    install+='root.OmoriLocaleUI.install(root,'+js({'direction':config['direction']})+');\n'
    install+='var original=ConfigManager.applyData;ConfigManager.applyData=function(config){original.apply(this,arguments);this.language=LanguageManager._language="en";};\n'
    install+='LanguageManager._language="en";root.OmoriLocale.siteLocale='+js(ctx.locale)+';}(this));\n'
    added=[{'name':'OmoriLocale_Bootstrap','status':True,'description':'Typed locale display bootstrap','parameters':{}},
           {'name':'OmoriLocale_Install','status':True,'description':'Locale display and font installation','parameters':{}}]
    cfg=[added[0]]+config_plugins+[added[1]]
    output={}
    for asset,value in results.items():
        if asset=='js/plugins.js':continue
        # Formatting changes alone do not justify redistributing a native asset.
        if not asset.startswith('js/') and value==originals[asset]:continue
        if asset.startswith('js/'):
            if not asset.startswith('js/plugins/'):continue
            raw=value.encode()
        elif asset in ctx.native:raw=yaml.safe_dump(value,allow_unicode=True,sort_keys=False,width=100000).encode()
        else:raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        if raw!=texts[asset].encode():output[asset]=raw
    output['js/plugins.js']=('var $plugins =\n'+json.dumps(cfg,ensure_ascii=False,indent=2)+';\n').encode()
    output['js/plugins/OmoriLocale_Bootstrap.OMORI']=bootstrap.encode()
    output['js/plugins/OmoriLocale_Install.OMORI']=install.encode()
    bindings=[]
    for row in mapping:
        if 'path' in row:
            p=row['path'];field=p[-1]
            if field not in ['name','displayName'] or (field=='name' and Path(row['asset']).stem not in ['Actors','Enemies','Items','Skills','Weapons','Armors','Classes','States']):raise ValueError('Unwired scalar mapping: '+row['id'])
            bindings.append({'id':row['id'],'kind':'mapName' if field=='displayName' else 'recordName','asset':row['asset'],'path':p,'targetSha256':sha(row['target'].encode())})
        elif row['asset'] in ctx.known:
            found=[b for b in variables if any(l['unitId']==row['id'] for l in b.get('labels',[]))]
            if not found:raise ValueError('Unwired variable mapping: '+row['id'])
            bindings.append({'id':row['id'],'kind':'variable','consumers':[{'asset':b['asset'],'commandPath':b['commandPath']} for b in found],'targetSha256':sha(row['target'].encode())})
        elif row['asset']=='js/plugins/GTP_OmoriFixes.OMORI':
            bindings.append({'id':row['id'],'kind':'errorMessage','asset':row['asset'],'targetSha256':sha(row['target'].encode())})
        elif row['asset']=='js/plugins/Custom Battle Action Text.OMORI':
            bindings.append({'id':row['id'],'kind':'emotion-display-operand','asset':row['asset'],'targetSha256':sha(row['target'].encode()),'branch':'Raw AFRAID selects its separately authored no-effect sentence; mapped display operand serves the generic template.'})
        else:raise ValueError('Unwired AST mapping: '+row['id'])
    return output, {'bindings':bindings,'variables':variables,'coreFunctions':core,'sources':source_proofs,'consumers':consumers}
