#!/usr/bin/env python3
"""Compile reviewed typed display consumers and loader-safe bootstrap plugins.

Every source-code edit has an exact original span. Native comparisons, database
names and variable values remain unchanged. The compiler never authors wording.
"""
import argparse
import copy
import json
import subprocess
import re
from pathlib import Path
from collections import defaultdict
from source_prepare import strict_json, save_json, sha
from text_resource_adapter import splice
from script_resource_adapter import (original_resource, programs, recover_program,
    program_edit, parsed_literals, at, put)
from assemble_ru_resources import read_pairs
from source_text_syntax import quick_macro_names

# Individually reviewed potential-name consumers in inventory 02. All omitted
# rows are native identity, asset, method, save-value or comparison consumers.
NONBATTLE=set([0,1,2,3,4,6,11,*range(16,42),45,*range(91,98),105,106,118,
    121,122,123,130,132,134,136,137,154,155,158,159,160,165,*range(170,176),
    *range(180,185),190,219,221,222,238,246,247,*range(250,260),261,262,311,316,
    *range(332,342),348,349,350,351,352,*range(367,374),375,376,379])

def js(value):return json.dumps(value,ensure_ascii=False)
def ast_calls(root,source):
    r=subprocess.run(['node','--expose-internals',str(root/'tools/display_calls.cjs')],input=source,text=True,capture_output=True)
    if r.returncode:raise ValueError('Consumer AST failed: '+r.stderr[-900:])
    return strict_json(r.stdout)
def span_edit(source,a,b,replacement,identity):
    return {'id':identity,'span':[a,b],'original':source.encode('utf-16-le')[2*a:2*b].decode('utf-16-le'),'replacement':replacement}
def source_edit(source,old,new,identity):
    if source.count(old)!=1:raise ValueError('Ambiguous source-bound adapter: '+identity)
    start=source.index(old);a=len(source[:start].encode('utf-16-le'))//2
    return span_edit(source,a,a+len(old.encode('utf-16-le'))//2,new,identity)
def expression_target(row):
    value=row['expression']
    if value.endswith('.name()'):return 'OmoriRu.name('+value[:-7]+')'
    if value.endswith('.displayName()'):return 'OmoriRu.mapName('+value[:-14]+')'
    if value.endswith('.name'):return 'OmoriRu.recordName('+value[:-5]+')'
    raise ValueError('Unknown reviewed typed consumer')

def argument_parser():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--combined',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--fonts',type=Path,required=True)
    return ap

def main():
    args=argument_parser().parse_args();root=Path(__file__).resolve().parent.parent
    if args.output.exists():raise ValueError('Preserve previous consumer compilation')
    pairs,corpus_sha,deps=read_pairs(root);known=programs(root)
    font_receipt=strict_json((args.fonts/'receipt.json').read_bytes())
    if font_receipt['status']!='passed-static':raise ValueError('Validated font input required')
    css=(args.fonts/'ru-fallback.css').read_text();font_probes=[]
    for family,filename,ranges in re.findall(r'@font-face \{font-family: ([^;]+); src: url\("([^"]+)"\); unicode-range: ([^;]+);\}',css):
        codes=[int(value.removeprefix('U+'),16) for value in ranges.split(',')]
        font_probes.append({'family':family,'file':filename,'text':''.join(chr(c) for c in codes)})
    if len(font_probes)!=css.count('@font-face') or {p['family'] for p in font_probes}!={'GameFont','OMORI_GAME','OMORI_GAME2'}:
        raise ValueError('Every fallback CSS face requires an exact glyph probe')
    font_inputs={'receiptSha256':sha((args.fonts/'receipt.json').read_bytes()),
                 'files':{p.name:sha(p.read_bytes()) for p in args.fonts.iterdir() if p.is_file() and p.name!='receipt.json'},
                 'probes':font_probes}
    macros=quick_macro_names(strict_json((root/'source/parameter-roles-8879120-01/parameters.json').read_bytes()))
    grouped=defaultdict(list)
    for u,e in pairs:
        if 'spanUtf16' in u:grouped[u['asset']].append((u,e))
    inventory=strict_json((root/'source/ru-display-consumers-2026-10-14-02.json').read_bytes())
    direct=defaultdict(list);nonbattle=[x for x in inventory if x['asset']!='js/plugins/Custom Battle Action Text.OMORI']
    selected=[x for i,x in enumerate(nonbattle) if i in NONBATTLE]
    selected.extend(x for x in inventory if x['asset']=='js/plugins/Custom Battle Action Text.OMORI'
        and not x['comparisons'] and 'parseNoEffectEmotion' not in x['calls'])
    embedded=strict_json((root/'source/ru-embedded-display-consumers-2026-10-14-01.json').read_bytes())
    selected.extend(embedded)
    for row in selected:
        asset=row['asset'];src=recover_program(known[asset],original_resource(root,known[asset]['originalAsset'])[1]) if asset in known else original_resource(root,asset)[0]
        replacement=expression_target(row)
        if row['asset']=='js/plugins/Omori Save & Load.OMORI' and row['expression']=='actor.name':replacement='OmoriRu.savedActor(info)'
        direct[asset].append(span_edit(src,*row['span'],replacement,'typed-name:'+str(row['span'])))
    # Locale compatibility: keep Cyrillic custom actor names accepted by the
    # native name getter and save-info validation in the EN overlay channel.
    asset='js/plugins/GTP_OmoriFixes.OMORI';src=original_resource(root,asset)[0]
    direct[asset].append(source_edit(src,'let englishOnly = /^[a-zA-Z0-9','let englishOnly = /^[a-zA-ZА-Яа-яЁё№0-9','ru-custom-name-validation'))
    # Save labels gain typed provenance; original fields stay raw.
    asset='js/plugins/Omori Save & Load.OMORI';src=original_resource(root,asset)[0]
    direct[asset].append(source_edit(src,'this.contents.drawText(info.location,','this.contents.drawText(OmoriRu.savedLocation(info),','save-location-view'))
    # Reuse the measured label/value geometry already proved in the other
    # locales. The legacy RU overlay used two overlapping fixed origins.
    direct[asset].append(source_edit(src,
        'this.contents.drawText(LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").level, loc_position[0], loc_position[1], 100, 24);\r\n    this.contents.drawText(actor.level, loc_position[0], loc_position[1], 70, 24, \'right\');',
        'OmoriLocaleUI.drawFileLevel(this, LanguageManager.getMessageData("XX_BLUE.Omori_Save_Load").level, actor.level, loc_position[1], 24);',
        'save-level-measured-label-value-gap'))
    # Native cursor indentation changes x but leaves maxWidth unchanged. Reserve
    # that indentation in the save/load command's actual Bitmap drawing width.
    cursor_offset='Window_OmoriFileCommand.prototype.customCursorRectTextXOffset = function() { return 40; }'
    direct[asset].append(source_edit(src,cursor_offset,cursor_offset+'\r\n'+
        'Window_OmoriFileCommand.prototype.customCursorRectTextWidthOffset = function() { return -this.customCursorRectTextXOffset(); };',
        'save-load-command-text-bounds'))
    # The title's English-sized hint bitmap cannot hold the Russian labels.
    # Size the shared row from the actual active font, labels and icon positions,
    # then anchor its rendered right edge to the native viewport.
    asset='js/plugins/Omori Title Screen.OMORI';src=original_resource(root,asset)[0]
    hint_anchor='  this._commandHints.bitmap.drawInputIcon("ok", 0, paddingY);'
    hint_layout='''  let confirmPosition = LanguageManager.getMessageData("XX_BLUE.Scene_OmoriTitleScreen").commandHints_confirm_position;
  let cancelPosition = LanguageManager.getMessageData("XX_BLUE.Scene_OmoriTitleScreen").commandHints_cancel_position;
  let confirmWidth = this._commandHints.bitmap.measureTextWidth(confirm);
  let cancelWidth = this._commandHints.bitmap.measureTextWidth(cancel);
  let hintWidth = Math.ceil(Math.max(eval(confirmPosition[0]) + confirmWidth,
    eval(cancelPosition[0]) + cancelWidth, iconSize + 15 + confirmWidth + iconSize) + 4);
  this._commandHints.bitmap.resize(hintWidth, this._commandHints.bitmap.height);
  this._commandHints.setFrame(0, 0, hintWidth, this._commandHints.bitmap.height);
  this._commandHints.position.set(Graphics.boxWidth - hintWidth, 0);
'''
    direct[asset].append(source_edit(src,hint_anchor,hint_layout+hint_anchor,'title-hint-measured-width'))
    # Keep steal callbacks/evals on native item name; map only format operand.
    asset='js/plugins/YEP_StealSnatch.OMORI';src=original_resource(root,asset)[0]
    direct[asset].append(source_edit(src,'target.name(), name, icon);','target.name(), (item ? OmoriRu.recordName(item) : name), icon);','steal-name-format'))
    # Display variable values only at native escape-code conversion sites.
    asset='js/rpg_windows.js';src=original_resource(root,asset)[0]
    calls=ast_calls(root,src)
    converter=next(x for x in calls if x['type']=='FunctionAssignment' and x['owner']=='Window_Base.prototype.convertEscapeCharacters')
    for call in calls:
        if call['type']=='CallExpression' and call['callee']=='$gameVariables.value' and converter['span'][0]<=call['span'][0]<converter['span'][1]:
            direct[asset].append(span_edit(src,call['span'][0],call['span'][0]+len('$gameVariables.value'),'OmoriRu.variable','display-variable-escape'))
    asset='js/rpg_objects.js';src=original_resource(root,asset)[0]
    direct[asset].append(source_edit(src,'TextManager.levelUp.format(this._name,','TextManager.levelUp.format(OmoriRu.name(this),','level-up-name'))
    for asset in ['js/rpg_managers.js','js/plugins/YEP_BattleEngineCore.OMORI']:
        src=original_resource(root,asset)[0]
        direct[asset].append(source_edit(src,'$gameTroop.enemyNames()','OmoriRu.enemyNames()','battle-start-enemy-display'))
    asset='js/plugins/Omori Battle System.OMORI';src=original_resource(root,asset)[0]
    short_names=[c for c in ast_calls(root,src) if c['type']=='CallExpression' and c['callee']=='DataManager.itemShortName']
    if len(short_names)!=2 or any(c['args'][0]['source']!='item' for c in short_names):raise ValueError('Battle short-name consumers changed')
    for c in short_names:
        a,b=c['span'];raw=span_edit(src,a,b,'','short-name')['original']
        direct[asset].append(span_edit(src,a,b,'OmoriRu.displayField(item, '+raw+')','battle-short-name:'+str(a)))
    asset='js/plugins/YIN - Minigame - Jukebox.OMORI';src=original_resource(root,asset)[0]
    direct[asset].append(source_edit(src,'$gameVariables.setValue(829, $dataItems[jukeboxCDs[i]].name)',
        'OmoriRu.setRecordVariable(829, $dataItems[jukeboxCDs[i]])','jukebox-native-name-variable'))
    asset='js/plugins/Omori Name Input.OMORI';src=original_resource(root,asset)[0]
    keyboard=strict_json((root/'runtime/ru-name-input-layout.json').read_bytes())
    direct[asset].append(source_edit(src,'this._currentLayout = VirtualKeyboard[language][this._layoutType]',
        'this._currentLayout = (language === "EN" && !this._ruLatin ? VirtualKeyboard.OMORI_RU : VirtualKeyboard[language])[this._layoutType]','ru-name-palette'))
    direct[asset].append(source_edit(src,'return res.concat(back).concat(l).concat(forward)\r\n    })',
        'return res.concat(back).concat(l).concat(forward)\r\n    })\r\n    if(language === "EN") {\r\n      if(this._currentLayout[1][0] !== " ") {throw new Error("RU keyboard padding mismatch");}\r\n      this._currentLayout[1][0] = "{ruLang}";\r\n    }','ru-name-language-key'))
    direct[asset].append(source_edit(src,'case "{lock}":\r\n        case "{tradch}":',
        'case "{ruLang}":\r\n          this._ruLatin = !this._ruLatin\r\n          SoundManager.playCursor()\r\n          this.refresh()\r\n          break;\r\n        case "{lock}":\r\n        case "{tradch}":','ru-name-language-switch'))
    end=len(src.encode('utf-16-le'))//2
    direct[asset].append(span_edit(src,end,end,'\nVirtualKeyboard.OMORI_RU = '+js({k:keyboard[k] for k in ['default','shift']})+';\nVirtualKeyboard["{ruLang}"] = '+js(keyboard['languageToggle']['label'])+';\n','ru-name-palette-data'))
    # Pizza notes resolve every word to an English image resource. Route only
    # this presentation surface through text; retain generateHouse and grading.
    asset='js/plugins/YIN - Minigame - PizzaDelivery.OMORI';src=original_resource(root,asset)[0]
    functions=ast_calls(root,src)
    for owner,target in [
        ('Window_PizzaDeliveryNote.prototype.refresh','function (text) { return OmoriRu.renderPizzaNote(this, text); }'),
        ('Game_Interpreter.prototype.checkImages',"function () { ImageManager.loadPicture('PIZZA-Background'); }")]:
        candidates=[x for x in functions if x['type']=='FunctionAssignment' and x['owner']==owner]
        if len(candidates)!=1:raise ValueError('Pizza presentation source owner changed')
        direct[asset].append(source_edit(src,candidates[0]['source'],target,'ru-pizza-presentation:'+owner))
    # Raw AFRAID still drives its original branch and actor comparison; its
    # separate display-name argument is used only in the output template.
    asset='js/plugins/Custom Battle Action Text.OMORI';src=original_resource(root,asset)[0]
    direct[asset].append(source_edit(src,'function parseNoEffectEmotion(tname, em)','function parseNoEffectEmotion(tname, em, displayName)','emotion-display-argument'))
    direct[asset].append(source_edit(src,'let finalString = `${tname}', 'let finalString = `${displayName}','emotion-display-template'))
    for call in ast_calls(root,src):
        if call['type']=='CallExpression' and call['callee']=='parseNoEffectEmotion':
            value=call['args'][0]['source']
            if not value.endswith('.name()'):raise ValueError('Unknown emotion name source')
            direct[asset].append(span_edit(src,call['span'][1]-1,call['span'][1]-1,', OmoriRu.name('+value[:-7]+')','emotion-call:'+str(call['span'][0])))
    # Error.message is a native identity: label the same Error object, then map
    # its message only in the exception display consumers.
    asset='js/plugins/GTP_OmoriFixes.OMORI';src=original_resource(root,asset)[0];calls=ast_calls(root,src)
    for u,e in grouped[asset]:
        if u['role']=='visible-display-mapping':
            call=next(x for x in calls if x['type']=='NewExpression' and x['callee']=='Error' and x['args'][0]['span']==u['spanUtf16'])
            a,b=call['span'];direct[asset].append(span_edit(src,a,a,'OmoriRu.error('+js(u['id'])+', ','error-open:'+u['id']))
            direct[asset].append(span_edit(src,b,b,')','error-close:'+u['id']))
    for asset in ['js/rpg_managers.js','js/plugins/YEP_CoreEngine.OMORI']:
        src=original_resource(root,asset)[0]
        direct[asset].append(source_edit(src,'e.name, e.message','e.name, OmoriRu.errorMessage(e)','error-display'))
    args.output.mkdir(parents=True);results=[];core=[];embedded_edits=defaultdict(lambda:defaultdict(list))
    for asset in sorted(set(grouped)|set(direct)):
        record=known.get(asset)
        if record:src=recover_program(record,original_resource(root,record['originalAsset'])[1])
        else:src=original_resource(root,asset)[0]
        edits=[program_edit(u,e,macros) for u,e in grouped[asset]]+direct[asset]
        # A formatted sink can contain a selected name call. Keep the sink edit
        # to its extra operand span, avoiding a duplicate call-expression edit.
        if asset=='js/plugins/YEP_StealSnatch.OMORI':
            special=next(e for e in edits if e['id']=='steal-name-format');special['span'][0]+=len('target.name(), ');special['original']=special['original'][len('target.name(), '):];special['replacement']=special['replacement'][len('target.name(), '):]
        dst=splice(src,edits,utf16=True);parsed_literals(root,asset,dst)
        if record:
            if 'linePaths' in record:
                lines=dst.splitlines(keepends=True)
                if len(lines)!=len(record['linePaths']):raise ValueError('Embedded adapter changed lines')
                for p,v in zip(record['linePaths'],lines):embedded_edits[record['originalAsset']][tuple(p)].append({'whole':v[:-1]})
            elif 'spanCodepoints' in record:embedded_edits[record['originalAsset']][tuple(record['parentPath'])].append({'id':asset,'span':record['spanCodepoints'],'original':src,'replacement':dst})
            else:embedded_edits[record['originalAsset']][tuple(record['parentPath'])].append({'whole':dst})
        elif asset.startswith('js/plugins/'):
            path=args.output/'plugins'/Path(asset).with_suffix('.js').name;path.parent.mkdir(exist_ok=True);path.write_text(dst)
        else:
            # Core files are protected by the loader. Install only reviewed
            # changed function assignments before native plugins capture aliases.
            owners=[x for x in ast_calls(root,src) if x['type']=='FunctionAssignment']
            nontrivial=[e for e in edits if e['replacement']!=e['original']]
            covered=set()
            for owner in owners:
                a,b=owner['span'];local=[e for e in nontrivial if a<=e['span'][0] and e['span'][1]<=b]
                if not local:continue
                value=owner['source'];pp=[]
                for e in local:
                    p=copy.deepcopy(e);p['span']=[e['span'][0]-a,e['span'][1]-a];pp.append(p);covered.add(e['id'])
                core.append({'asset':asset,'owner':owner['owner'],'source':value,'target':splice(value,pp,utf16=True)})
            if covered!={e['id'] for e in nontrivial}:raise ValueError('Unbound protected core edit')
        results.append({'asset':asset,'sourceSha256':sha(src.encode()),'compiledSha256':sha(dst.encode()),'displayEdits':direct[asset]})
    # Mixed note programs and scalar note segments share the same original
    # parent. Merge all spans once, never replace a previously localized note.
    combined=strict_json((args.combined/'receipt.json').read_bytes());resources={r['originalAsset']:r for r in combined['resources']}
    for asset,fields in embedded_edits.items():
        _,original=original_resource(root,asset);tree=copy.deepcopy(original)
        # Start from the exact merged resource for ordinary/scalar targets.
        current=strict_json((args.combined/resources[asset]['output']).read_bytes())
        for path,edits in fields.items():
            if 'whole' in edits[0]:
                if len(edits)!=1:raise ValueError('Duplicate embedded parent');
                put(current,path,edits[0]['whole'])
            else:
                sibling=[(u,e) for u,e in pairs if u['asset']==asset and tuple(u.get('path',[]))==path and ('spanCodepoints' in u or 'span' in u)]
                from text_resource_adapter import exact_span_edit
                edits+= [exact_span_edit(u,e['target'],macros) for u,e in sibling]
                put(current,path,splice(at(original,path),edits))
        out=args.output/'data'/Path(asset).with_suffix('.json').name;out.parent.mkdir(exist_ok=True);save_json(out,current)
    # Build variable bindings from exact delivered command identity and native
    # command parameters. The database field is not mutated or renamed.
    variable_bindings=[]
    mapping=strict_json((args.combined/'display-mappings.json').read_bytes())
    for row in mapping['entries']:
        if row['asset'] not in known:continue
        rec=known[row['asset']];asset=rec['originalAsset'];_,tree=original_resource(root,asset)
        if 'linePaths' in rec:
            command_path=rec['linePaths'][0][:-2];var_id=23;code=355
        else:
            command_path=rec['parentPath'][:-2];cmd=at(tree,command_path)
            if cmd['code']!=122 or cmd['parameters'][2:4]!=[0,4] or cmd['parameters'][0]!=cmd['parameters'][1]:raise ValueError('Variable binding is not direct assignment')
            var_id=cmd['parameters'][0];code=122
        cmd=at(tree,command_path)
        variable_bindings.append({'asset':asset,'commandPath':command_path,'code':code,'parameters':json.dumps(cmd['parameters'],ensure_ascii=False,separators=(',',':')),
            'labels':[{'variableId':var_id,'unitId':row['id']}]})
    dynamic=strict_json((root/'source/ru-name-variable-bindings-2026-10-14-02.json').read_bytes())
    for binding in dynamic['bindings']:
        record=known[binding['sourceProgram']]
        if record['rawSha256']!=binding['sourceProgramSha256']:raise ValueError('Dynamic name program changed')
        _,tree=original_resource(root,binding['asset']);command=at(tree,binding['commandPath'])
        if json.dumps(command['parameters'],ensure_ascii=False,separators=(',',':'))!=binding['parameters']:raise ValueError('Dynamic name command changed')
    variable_bindings.extend(dynamic['bindings'])
    from source_password_bindings import collect as collect_password_bindings
    password_bindings=collect_password_bindings(root)
    password_evidence=root/'source/ru-password-catalog-bindings-2026-10-14-01.json'
    if password_bindings!=strict_json(password_evidence.read_bytes()):raise ValueError('Password source binding evidence changed')
    byid={u['id']:(u,e) for u,e in pairs}
    for binding in password_bindings['bindings']:
        for label in binding['labels']:
            unit,entry=byid[label['catalogUnitId']];logical,display=byid[label['unitId']]
            if logical['source']!=unit['source']:raise ValueError('Password logical concept mismatch')
            label['catalogTarget']=entry['target']
    variable_bindings.extend(password_bindings['bindings'])
    # Parameter overrides run first, after PluginManager.setup has populated
    # parameter tables and before native plugin scripts read them.
    _,original_config=original_resource(root,'js/plugins.js')
    cfg=parse_config((args.combined/resources['js/plugins.js']['output']).read_bytes())
    parameter_edits=[]
    for original,target in zip(original_config,cfg):
        if original['name']!=target['name']:raise ValueError('Plugin order/name changed')
        for key,value in target['parameters'].items():
            if value!=original['parameters'][key]:parameter_edits.append({'plugin':original['name'].lower(),'key':key,'source':original['parameters'][key],'target':value})
    password_forms=strict_json((root/'runtime/ru-password-forms.json').read_bytes())
    password_template=next(e['target'] for u,e in pairs if u['id']=='languages/en/XX_MELON.HERO#["message_49","text"]')
    contextual_forms=[]
    _,actors=original_resource(root,'data/Actors.KEL')
    for unit,entry in pairs:
        for placeholder,form in entry.get('placeholderForms',{}).items():
            match=re.fullmatch(r'\\n\[(\d+)\]',placeholder)
            if not match or not unit['asset'].startswith('languages/en/') or unit['path'][-1]!='text':raise ValueError('Unbound contextual form')
            actor_id=int(match[1]);contextual_forms.append({'id':unit['id'],'file':Path(unit['asset']).stem,
                'key':unit['path'][0],'target':entry['target'],'actorId':actor_id,'nativeName':actors[actor_id]['name'],
                'placeholder':placeholder,'form':form['targetForm'],'case':form['case']})
    boot=((root/'tools/multilingual/delivery/ui_layout.js').read_text()+'\n'+(root/'runtime/ru-engine-display.js').read_text()+'\n'+(root/'runtime/ru-pizza-note.js').read_text()+'\n(function(root){\n'+
        'function nativeFunctionSource(s){return s.replace(/\\r\\n?/g, \"\\n\").replace(/^function[ \\t]*\\(/, \"function(\");}\n'+
        'root.OmoriRu = root.OmoriRuEngineDisplay.create('+js(mapping['entries'])+','+js(variable_bindings)+',root,'+js(password_forms)+','+js(password_template)+','+js(contextual_forms)+');\n'+
        'root.OmoriRu.renderPizzaNote = root.OmoriRuPizzaNote.render;\n'+
        'var edits='+js(parameter_edits)+'; edits.forEach(function(e){var config=$plugins.filter(function(p){return p.name.toLowerCase()===e.plugin;});if(config.length!==1 || config[0].parameters[e.key]!==e.source)throw new Error("RU plugin parameter input mismatch: "+e.plugin+"/"+e.key);config[0].parameters[e.key]=e.target;});\n')
    for row in core:
        boot+='if(nativeFunctionSource('+row['owner']+'.toString()) !== nativeFunctionSource('+js(row['source'])+'))throw new Error("RU core function mismatch: '+row['owner']+'");\n'+row['owner']+' = '+row['target']+';\n'
    boot+='}(this));\n'
    (args.output/'plugins/OmoriRu_Bootstrap.js').write_text(boot)
    install=(root/'runtime/ru-font-ready.js').read_text()+'\n(function(root){root.OmoriLocaleUI.configure(root,{direction:"ltr"});root.OmoriRu.install();root.OmoriRuFonts.install(root,'+js(font_probes)+');}(this));\n'
    (args.output/'plugins/OmoriRu_Install.js').write_text(install)
    parsed_literals(root,'RU-install',install)
    parsed_literals(root,'RU-bootstrap',boot)
    compiled_outputs={str(p.relative_to(args.output)):sha(p.read_bytes()) for p in sorted(args.output.rglob('*')) if p.is_file()}
    save_json(args.output/'receipt.json',{'status':'passed-static-assembly','corpusManifestRawSha256':corpus_sha,
        'recipeDependencies':{n:sha((root/n).read_bytes()) for n in ['tools/compile_ru_display.py','tools/multilingual/delivery/ui_layout.js','tools/display_calls.cjs','runtime/ru-engine-display.js','runtime/ru-pizza-note.js','runtime/ru-font-ready.js','runtime/ru-password-forms.json','runtime/ru-name-input-layout.json','source/ru-name-variable-bindings-2026-10-14-02.json','tools/source_name_variable_bindings.py','tools/source_password_bindings.py','source/ru-password-catalog-bindings-2026-10-14-01.json']},
        'compiledOutputs':compiled_outputs,'authorDependencies':{p:h for p,h in deps.items() if p.startswith('translation/ru/batches/')},'fontInputs':font_inputs,
        'combinedReceiptSha256':sha((args.combined/'receipt.json').read_bytes()),'sources':results,'coreFunctions':core,
        'variableBindings':variable_bindings,'parameterEdits':parameter_edits,'contextualForms':contextual_forms,
        'scalarMappings':sum('path' in r for r in mapping['entries']),'mappedAstOccurrences':sum('spanUtf16' in r for r in mapping['entries']),
        'runtime':'not-run','loaderBoot':'not-run','independentReview':'pending',
        'legacySaveLabels':'Old save metadata without typed actor/map provenance stays native; runtime validation pending.'})
    print({'status':'passed-static-assembly','sourceAssets':len(results),'coreFunctions':len(core),'variableBindings':len(variable_bindings),'parameterFields':len(parameter_edits)})

from script_resource_adapter import parse_config
if __name__=='__main__':main()
