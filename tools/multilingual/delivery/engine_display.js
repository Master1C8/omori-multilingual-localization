/* Typed display adapters. Native names, values, keys and comparisons stay raw. */
(function(root) {
  'use strict';
  function create(entries, variableBindings, env, contextualForms) {
    var labels=Object.create(null), byId=Object.create(null), commandLabels=new WeakMap(), errors=new WeakMap(), activePasswordBinding=null;
    entries.forEach(function(row) {
      byId[row.id]=row;
      if(row.path)labels[JSON.stringify([row.asset,row.path])]=row;
    });
    function label(id,value) {var row=byId[id];return row && row.source===value ? row.target : value;}
    function lookup(asset,path,value) {
      var row=labels[JSON.stringify([asset,path])];
      return row && row.source===value ? row.target : value;
    }
    var kinds=['Actors','Enemies','Items','Skills','Weapons','Armors','Classes','States'];
    function recordName(record) {
      if(!record)return '';
      for(var i=0;i<kinds.length;i++) {
        var data=env['$data'+kinds[i]];
        if(data && record.id && data[record.id]===record)
          return lookup('data/'+kinds[i]+'.KEL',[record.id,'name'],record.name);
      }
      return record.name;
    }
    function recordBinding(record,upper) {
      if(!record)return null;
      for(var i=0;i<kinds.length;i++) {
        var data=env['$data'+kinds[i]];
        if(data && record.id && data[record.id]===record) {
          var row=labels[JSON.stringify(['data/'+kinds[i]+'.KEL',[record.id,'name']])];
          if(row && row.source===record.name)return {unitId:row.id,rawValue:upper?record.name.toUpperCase():record.name,upper:!!upper};
        }
      }
      return null;
    }
    function battlerBinding(battler) {
      if(!battler)return null;
      var raw=battler.name(),row,suffix='';
      if(battler.isActor && battler.isActor())row=labels[JSON.stringify(['data/Actors.KEL',[battler.actorId(),'name']])];
      else if(battler.isEnemy && battler.isEnemy()) {
        row=labels[JSON.stringify(['data/Enemies.KEL',[battler.enemyId(),'name']])];
        suffix=battler._plural?battler._letter:'';
      }
      return row && raw===row.source+suffix ? {unitId:row.id,rawValue:raw,suffix:suffix} : null;
    }
    function setRecordVariable(id,record) {
      var vars=env.$gameVariables,result=vars.setValue(id,record.name),binding=recordBinding(record,false);
      if(binding && vars.value(id)===binding.rawValue) {
        if(!vars._omoriLocaleDisplayLabels)vars._omoriLocaleDisplayLabels={};
        vars._omoriLocaleDisplayLabels[id]=binding;
      }
      return result;
    }
    function name(battler) {
      if(!battler)return '';
      var raw=battler.name();
      if(battler===env.$gameParty) {
        var members=battler.battleMembers();
        if(!members.length)return raw;
        return members.length===1 ? name(battler.leader()) : env.TextManager.partyName.format(name(battler.leader()));
      }
      if(battler.isActor && battler.isActor())
        return lookup('data/Actors.KEL',[battler.actorId(),'name'],raw);
      if(battler.isEnemy && battler.isEnemy()) {
        var base=battler.originalName();
        var translated=lookup('data/Enemies.KEL',[battler.enemyId(),'name'],base);
        var suffix=battler._plural ? battler._letter : '';
        return raw===base+suffix ? translated+suffix : raw;
      }
      return raw;
    }
    function mapName(map) {
      var raw=map.displayName();
      if(map._overrideDisplayName)return raw;
      return lookup('data/Map'+('000'+map.mapId()).slice(-3)+'.KEL',['displayName'],raw);
    }
    function displayField(record,value) {
      return record && value===record.name ? recordName(record) : value;
    }
    function enemyNames() {
      var troop=env.$gameTroop, originals=troop.enemyNames(),members=troop.members();
      return originals.map(function(raw) {
        for(var i=0;i<members.length;i++) {
          var enemy=members[i];
          if(enemy.isAlive() && enemy.originalName()===raw)
            return lookup('data/Enemies.KEL',[enemy.enemyId(),'name'],raw);
        }
        return raw;
      });
    }
    function savedActor(info) {
      var data=info.actorData;
      return info.omoriLocaleActorId ? lookup('data/Actors.KEL',[info.omoriLocaleActorId,'name'],data.name) : data.name;
    }
    function savedLocation(info) {
      return info.omoriLocaleMapId ? lookup('data/Map'+('000'+info.omoriLocaleMapId).slice(-3)+'.KEL',['displayName'],info.location) : info.location;
    }
    function error(id,value) {
      var row=byId[id];
      if(row && row.source===value.message)errors.set(value,id);
      return value;
    }
    function errorMessage(value) {
      var row=byId[errors.get(value)];
      return row && row.source===value.message ? row.target : value.message;
    }
    function at(data,path) {for(var i=0;i<path.length;i++){if(data==null)return null;data=data[path[i]];}return data;}
    function bindAsset(asset,data) {
      variableBindings.forEach(function(binding) {
        if(binding.asset!==asset)return;
        var command=at(data,binding.commandPath);
        if(command)commandLabels.delete(command);
        if(command && command.code===binding.code && JSON.stringify(command.parameters)===binding.parameters) {
          if(binding.passwordCatalog) {
            var list=at(data,binding.commandPath.slice(0,-1)), index=binding.commandPath[binding.commandPath.length-1];
            if(!binding.sourceCommands.every(function(expected,i) {
              return JSON.stringify(list[index+i])===JSON.stringify(expected);
            }))return;
          }
          commandLabels.set(command,binding);
        }
      });
    }
    function variable(id) {
      var vars=env.$gameVariables,raw=vars.value(id),metadata=vars._omoriLocaleDisplayLabels;
      var binding=metadata && metadata[id],row=binding && byId[typeof binding==='string'?binding:binding.unitId];
      if(typeof binding==='string')return row && row.source===raw ? row.target : raw;
      if(binding && row && binding.rawValue===raw &&
          raw===(binding.upper?row.source.toUpperCase():row.source)+(binding.suffix||''))
        return (binding.upper?row.target.toUpperCase():row.target)+(binding.suffix||'');
      return raw;
    }
    function commandBinding(command,interpreter) {
      var binding=commandLabels.get(command);
      if(!binding || command.code!==binding.code || JSON.stringify(command.parameters)!==binding.parameters)return null;
      if(binding.passwordCatalog && (!interpreter._list || !binding.sourceCommands.every(function(expected,i) {
        return JSON.stringify(interpreter._list[interpreter._index+i])===JSON.stringify(expected);
      })))return null;
      return binding;
    }
    function commitCommand(command,interpreter,verifiedBinding) {
      var binding=arguments.length>2 ? verifiedBinding : commandBinding(command,interpreter);
      if(!binding)return;
      var vars=env.$gameVariables;
      if(!vars._omoriLocaleDisplayLabels)vars._omoriLocaleDisplayLabels={};
      if(binding.dynamicName) {
        var descriptor=binding.dynamicName,record,nameBinding;
        if(descriptor.kind==='database')record=env['$data'+descriptor.database][descriptor.recordId];
        if(descriptor.kind==='gacha-item')record=interpreter._gachaItem;
        if(descriptor.kind==='troop-member')nameBinding=battlerBinding(env.$gameTroop.members()[descriptor.index]);
        else nameBinding=recordBinding(record,descriptor.upper);
        if(nameBinding && vars.value(descriptor.variableId)===nameBinding.rawValue)
          vars._omoriLocaleDisplayLabels[descriptor.variableId]=nameBinding;
        return;
      }
      binding.labels.forEach(function(label) {
        var row=byId[label.unitId];
        if(row && vars.value(label.variableId)===row.source)
          vars._omoriLocaleDisplayLabels[label.variableId]=label.unitId;
      });
    }
    function install() {
      var proto=env.Game_Variables.prototype, setValue=proto.setValue;
      proto.setValue=function(id,value) {
        if(this._omoriLocaleDisplayLabels)delete this._omoriLocaleDisplayLabels[id];
        if(activePasswordBinding && this===env.$gameVariables) {
          activePasswordBinding.labels.forEach(function(label) {
            var row=byId[label.unitId];
            if(label.variableId===id && value===label.catalogTarget && row)
              value=row.source;
          });
          arguments[1]=value;
        }
        return setValue.apply(this,arguments);
      };
      [122,355].forEach(function(code) {
        var p=env.Game_Interpreter.prototype, key='command'+code, original=p[key];
        p[key]=function() {
          var command=this.currentCommand(), prior=activePasswordBinding, binding=commandBinding(command,this), result;
          activePasswordBinding=binding && binding.passwordCatalog ? binding : null;
          try {result=original.apply(this,arguments);} finally {activePasswordBinding=prior;}
          commitCommand(command,this,binding); return result;
        };
      });
      var dm=env.DataManager, loadMap=dm.loadMapData, onLoad=dm.onLoad, pendingMap;
      dm.loadMapData=function(id){pendingMap=id;return loadMap.apply(this,arguments);};
      dm.onLoad=function(data) {
        var result=onLoad.apply(this,arguments);
        if(data===env.$dataMap && pendingMap!=null)
          bindAsset('data/Map'+('000'+pendingMap).slice(-3)+'.KEL',data);
        if(data===env.$dataCommonEvents)bindAsset('data/CommonEvents.KEL',data);
        if(data===env.$dataTroops)bindAsset('data/Troops.KEL',data);
        return result;
      };
      if(env.$dataCommonEvents)bindAsset('data/CommonEvents.KEL',env.$dataCommonEvents);
      if(env.$dataTroops)bindAsset('data/Troops.KEL',env.$dataTroops);
      var makeInfo=dm.makeSavefileInfo;
      dm.makeSavefileInfo=function() {
        var info=makeInfo.apply(this,arguments),actor=env.$gameParty.leader();
        if(info.actorData && actor)info.omoriLocaleActorId=actor.actorId();
        if(info.location && env.$gameMap)info.omoriLocaleMapId=env.$gameMap.mapId();
        return info;
      };
      if(contextualForms && contextualForms.length && env.LanguageManager) {
        var languageManager=env.LanguageManager,readText=languageManager.getTextData;
        languageManager.getTextData=function(file,key) {
          var result=readText.apply(this,arguments);
          if(!result || typeof result.text!=='string')return result;
          var text=result.text;
          contextualForms.forEach(function(binding) {
            if(binding.file!==file || binding.key!==key || binding.target!==text)return;
            var actor=env.$gameActors.actor(binding.actorId);
            if(actor && actor.name()===binding.nativeName)
              text=text.split(binding.placeholder).join(binding.form);
          });
          if(text===result.text)return result;
          var view={};Object.keys(result).forEach(function(k){view[k]=result[k];});view.text=text;return view;
        };
      }
    }
    return {label:label,lookup:lookup,name:name,recordName:recordName,mapName:mapName,
      displayField:displayField,enemyNames:enemyNames,savedActor:savedActor,savedLocation:savedLocation,
      variable:variable,bindAsset:bindAsset,commitCommand:commitCommand,install:install,
      error:error,errorMessage:errorMessage,
      recordBinding:recordBinding,battlerBinding:battlerBinding,setRecordVariable:setRecordVariable};
  }
  var api={create:create};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.OmoriLocaleEngineDisplay=api;
}(typeof globalThis!=='undefined'?globalThis:this));
