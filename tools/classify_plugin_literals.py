#!/usr/bin/env python3
"""Conservative source roles for original plugin/core AST literals."""
import argparse
from collections import Counter
import re
from source_prepare import save_json, sha, strict_json

TECHNICAL = {'parameters', 'contains', 'includes', 'indexOf', 'startsWith', 'endsWith',
             'setHandler', 'isSymbolEnabled', 'isHandled', 'findSymbol', 'selectSymbol',
             'getMessageData', 'getTextData', 'getPluginText', 'getSystemText', 'getDatabaseText',
             'loadSystem', 'loadCharacter', 'loadPicture', 'loadAtlas', 'loadFace', 'loadBitmap',
             'loadBgm', 'loadBgs', 'playBgm', 'playBgs', 'playSe', 'playMe',
             'addCategory', 'removeStateCategoryAll', 'isStateCategoryAffected', 'isEmotionAffected',
             'getParamId', 'isInputTriggered', 'isPressed', 'isTriggered', 'isRepeated',
             'setWaitMode', 'requestEffect', 'pushCommand', 'hasOwnProperty', 'keys', 'defineProperty',
             'require', 'getter', 'readFile', 'readFileSync', 'writeFile', 'writeFileSync',
             'writeToFile', 'writeToFileAsync', 'unlink', 'unlinkSync', 'existsSync',
             'getContext', 'createElement', 'getElementsByTagName', 'getExtension', 'overrideMimeType',
             'loadDataFile', 'loadScript', 'loadParallax', 'loadFont', 'loadSystemSmooth',
             'reserve', 'reserveSystem', 'reservePicture', 'reserveBitmap', 'reserveNormalBitmap',
             'reserveAudio', 'reserveParallax', 'createBuffer', 'loadBattleback1',
             'setActionState', 'requestMotion', 'startMotion', 'forceMotion', 'getSideviewMotion',
             'isBattleSystem', 'isLifeStealState', 'makeLifeStealKey', 'isSideviewDimensions',
             'inputKeyCode', 'getInputName', 'getModifierState', 'isLongPressed',
             'readFlag', 'readVolume', 'getParamNumber', 'getParamBoolean', 'callHandler',
             'setLoadingImage', 'getCurrentHandValue', 'setMovementGraphicData',
             'namedItem', 'getLifeStealRate', 'getLifeStealFlat', 'magicSteal', 'lifeSteal',
             'unlockAchievement', 'setMessageAnchor', 'setMessagePositionX', 'setMessagePositionY',
             'removeHearts', 'removeHorrorEffect', 'setHorrorEffectToValue', 'setupLetterEffect',
             'startEffect', 'switchPhase', 'showActionImage', 'setPictureDisplayLayer',
             'loadSystemSmooth', 'addMapFog', 'addRequiredAtlas', 'addEventListener', 'removeEventListener',
             'easingFunctions', 'setEasingFunction', 'processMoveRouteSelfSwitch'}
TECHNICAL.update({'isOptionValid', 'fillRect', 'fillAll', 'drawCircle', 'gradientFillRect',
                 'requestBitmap', 'setUp', 'on', 'emit', 'needsCommand', 'setImage', 'hasCategory',
                 'setValueExt', 'getOwnPropertyDescriptor', 'canPlayType', 'convertNameToLanguage',
                 'changeActor', 'updateIndexFromDirection', 'changeTextColor', '_get', '_createClass',
                 'isFontLoaded', 'setAttribute', 'drawInputIcon', 'match', 'mapRegenUpdateCheck',
                 'releaseContainer', 'addContainer', 'addContainerItem', 'releaseItem', 'define',
                 'playDangerBgs', 'drawKeyIcon', 'setTextList', 'drawAlginedKeyIcon', 'readFromFile',
                 'toLocaleString', 'processMoveHugWall', 'randomizeArray', 'message', 'removeItem',
                 'fetch', 'fetchWithRetry', 'openExternal', 'basename', 'playStaticSe', 'execCommand',
                 'setCategory', 'drawCoinText', 'drawBetText', 'readConfigBattleCamera', 'fromVideo',
                 '_createFontLoader', 'createLoader', 'createMacBuiltin', 'playVideo', 'canPlayVideoType',
                 'actionMoveX', 'actionMoveY', 'targetPosX', 'targetPosY', 'setupResults', 'warning'})
DISPLAY = {'drawText', 'drawTextEx', 'addText', 'setHelpText', 'setText', 'alert', 'confirm', 'prompt'}
TECH_TABLES = {'this._badWords', 'KeyboardInput.keyNames', 'Input.keyMapper', 'Input.gamepadMapper',
               'VirtualKeyboard.Z2P', 'DataManager._databaseFiles', 'DataManager.locationNamesPerLanguage',
               'DataManager.chapterNamesPerLanguage', 'DataManager.actorNamesPerLanguage',
               'Game_Troop.LETTER_TABLE_HALF', 'Game_Troop.LETTER_TABLE_FULL', 'Yanfly.Aura.Types',
               'CHO', 'JUNG', 'JONG', 'CONSONANTS', 'COMPLEX_CONSONANTS', 'COMPLEX_VOWELS',
               'COMPLETE_CHO', 'COMPLETE_JUNG', 'COMPLETE_JONG'}
TECH_ASSIGNMENTS = {'evalMode', 'evalType', 'customMode', 'keys', 'key', 'this._phase', 'this._phaseSteps',
    'this._returnPhase', 'condition', 'eval', 'pass', 'code', 'formula', 'obj.steal', 'obj.stealType',
    'Yanfly.tx', 'se', 'bgm', 'folder', 'path', 'url', 'type', 'this._rockResult', 'source', 'commandName',
    'BattleManager._retryObjList', 'this._cameraFocusPosX', 'this._cameraFocusPosY', '_propertyWhitelist',
    'BattleManager.actionMoveXLocation', 'Yanfly.MsgMacroArr[Yanfly.i]', 'this._imageReservationId',
    '$gameTemp._addToFinishActions', 'array[array.length]', 'initCheckList', 'titleTextBitmap', 'lightbulbBitmap',
    'stringBitmap', 'linesBitmap', 'townsPeople', 'regEx', 'layers', 'atlasPath', 'omoriBitmap', 'hit',
    'this._dataClass', 'data.name', 'layerList', '_relativeProperties', 'this._activationType', 'arr',
    'this._vehicleType', 'command', 'this._characterMovementGraphics.climbing', 'this.searchActions',
    'obj.finishActions', 'obj.setupActions', 'IMMORTAL_COMMAND', 'this._step', 'steps', 'ekgName',
    'KeyboardInput.keyMapper', 'KeyboardInput.gamepadNames', 'toneKeys', '_blendModes', 'letterEffects',
    'obj.critMult', 'obj.flatCrit', 'suits', 'types', 'elite', 'this._anim', 'atlasChecks', 'mode', 'motion',
    'motions', 'this.options', 'this.type', 'e.f', 'rule', 'encryptedExt', 'pluginName', 'algorithm',
    'mapName', 'chars', 'tagName', 'backgroundName', 'symbol', '_originIndices', 'realPath', 'this._aiTarget',
    'evalKey', 'keyName', 'Yanfly.line', 'obj.gauge1', 'obj.gauge2', 'obj.gauge3', 'obj.critRate',
    'Yanfly.sName', 'Yanfly.oName', 'Yanfly.s1', 'this._playerPreviousPlay', 'this._opponentPreviousPlay',
    'this._player', 'addon', 'this._preferredAxis', 'filePath', 'this._weatherType',
    'AudioManager._defaultReservationId', 'EXA.FC.pluginParams.allowedList', 'command.parameters[0]',
    '$gameMap.savedCamTarget', 'this.savedCamTarget', 'tmp', 'this._defaultInputIcons', 'this._inputType',
    'this._retryCursorSprite', 'particleName', 'reservationId', 'this._pictureDisplayLayer', 'obj',
    'data[name]', "window['$' + key]", 'layer', "layers['_animation' + i]", 'this._facingDirection',
    're', 'this._waitMode', 'property', 'this._graphicsName', '_loop', 'this._stepAnimationBehavior',
    'rate', 'flat', 'obj.gaugeIcon1', 'obj.gaugeIcon2', 'obj.gaugeIcon3', 'this._msgWindowPositionX',
    'this._msgWindowPositionY', 'obj.removeCategory[category]', 'this.name', 'champ', 'this._power',
    'this._type', 'this._rendererType', 'options', 'menubar', 'this._vehicles[0]', 'this._vehicles[1]',
    'this._vehicles[2]', 'methodName', 'this._category', 'align', 'this._mode', 'prefix'}

# Return contracts established by the owning original functions: glyph/resource,
# motion/dispatch, format and identity values are consumed before display.
TECH_RETURNS = {'Game_Actor.prototype.faceSaveLoad', 'DataManager.getNotetagAuraType',
    'Game_Player.prototype.footprintGraphicsName', 'Game_CharacterBase.prototype.footprintGraphicsName',
    'DataManager.getPassiveConditionParamRate', 'BattleManager.getParamId',
    'DataManager.processCORENotetags1', 'DataManager.processEquipNotetags2',
    'StorageManager.webStorageKey', 'Game_Interpreter.prototype.temporaryReservationId',
    'Game_Battler.prototype.getStateEmotion', 'Scene_Battle.prototype.commandItem',
    'Window_OmoriStopTheArrow.prototype.setup', 'Window_Candidate',
    'DataManager.hangmanWord', 'Window_Base.prototype.standardFontFace',
    'Bitmap.prototype._makeFontNameText', 'AudioManager.audioFileExt',
    'Game_Interpreter.prototype.videoFileExt', 'Utils.RPGMAKER_NAME', 'Utils.RPGMAKER_VERSION',
    'Decrypter._ignoreList', 'Decrypter.SIGNATURE', 'DataManager._globalId', 'AudioManager._path',
    'PluginManager._path', 'JsonEx._resetPrototype'}


def classify(row):
    value, context = row['source'], row['context']
    if row['role'] == 'preserve-exactly':
        return row['role'], row['reason']
    if row['asset'].endswith('/GTP_OmoriFixes.OMORI') and value in {'Steam has not been detected.', 'This game does not work in SDK mode.'}:
        return 'visible-display-mapping', 'System error message also controls native error-renderer comparison. Preserve original thrown identity and translate only its final display through a predetermined mapping.'
    if context.get('callMethod') == 'parseNoEffectEmotion' and context.get('callArgumentIndex') == 1 and 'afraid' in value.lower():
        return 'visible-display-mapping', 'Emotion feedback argument also selects the afraid branch. Preserve original discriminator and localize its displayed form separately.'
    if context['parentType'] == 'SwitchCase':
        return 'preserve-exactly', 'Switch dispatch/comparison label.'
    assignment = context.get('assignmentTarget') or ''
    function = context.get('functionName') or assignment
    # A whole function's UI/error purpose cannot turn its DOM/CSS/font,
    # comparison or lookup operands into wording. Resolve declared native
    # consumer contracts before broad enclosing-function display heuristics.
    if context.get('callMethod') in TECHNICAL:
        return 'preserve-exactly', 'Declared native consumer argument; takes precedence over enclosing UI/error function scope.'
    if re.search(r'\.style\.[A-Za-z]+$', assignment):
        return 'preserve-exactly', 'CSS declaration value; preserve grammar, geometry and font identifiers.'
    callee = (context.get('ancestorCalls') or [{}])[0].get('callee', '')
    if callee.startswith('Yanfly.BEC.DefaultAction') or callee == 'Yanfly.Param.CounterConditions.push':
        return 'preserve-exactly', 'Native action/condition dispatch array.'
    if context.get('callMethod') == 'push' and assignment == 'BattleManager':
        return 'preserve-exactly-program', 'Native scripted action queue; source command/program must retain mechanical behavior.'
    if row['asset'].endswith('/YSP_VideoPlayer.OMORI') and (assignment in {'t.exports', 'e.n', 'i', 'r', 'e'} or context.get('callMethod') == 'r'):
        return 'preserve-exactly', 'Bundled ES compatibility/video DOM module implementation and diagnostics.'
    if function in {'_classCallCheck', '_possibleConstructorReturn', '_inherits', 'defineProperties', 'get'} and row['asset'].endswith('/YED_Tiled.OMORI'):
        return 'preserve-exactly', 'Compiled class compatibility/property machinery.'
    if function in {'_validateEasingFunction', '_validateEasingProperty', '_parseCommandParam',
                    'disassemble', 'Sprite.prototype.setBlendColor', 'Sprite.prototype.setColorTone',
                    'JsonEx._encode', 'Decrypter.decryptArrayBuffer', 'r.replacements.set'}:
        return 'preserve-exactly', 'Internal parser/programmer guard diagnostic or command schema.'
    if value.startswith("Couldn't find the parameters of Archeia_"):
        return 'preserve-exactly', 'Developer plugin dependency diagnostic.'
    if context.get('propertyKey') in {'fontFamily', 'align'}:
        return 'preserve-exactly', 'Native font/alignment descriptor.'
    if assignment.startswith('VirtualKeyboard[') or assignment == 'obj.stateCounterSettings[\'align\']':
        return 'preserve-exactly', 'Keyboard glyph/input mapping or counter alignment.'
    if assignment in {'Omori_FPSCounter.prototype._update', 'this._labelDiv.textContent'}:
        return 'preserve-exactly', 'Native FPS/ms instrumentation unit.'
    if context.get('callMethod') == 'textWidth' or function.startswith('Game_BattlerBase.prototype.gauge'):
        return 'preserve-exactly', 'Gauge type or native width measurement probe; actual labels are catalogued.'
    if function in {'Game_System.prototype.activateGameOverlay', 'DataManager.getPassiveConditionParam',
                    'Scene_OmoriPhotoAlbum.prototype.prepare', 'ImageManager.loadEmptyBitmap',
                    'Scene_SpaceInvader.prototype.setupEnemies', 'Game_Action.prototype.makeBattleEngineCoreStealWait'}:
        return 'preserve-exactly', 'Bound platform, formula, album/resource/animation or mechanical queue contract.'
    if function.startswith('Scene_OmoriTitleScreen.prototype.playBg') or function == 'DataManager.processStealNotetags2':
        return 'preserve-exactly', 'Audio resource or steal-type dispatch.'
    if assignment in {'_TDS_.ActiveChainSkills.params.activeSkillSound', 'me', 'Liquid.Param.EventconSheet',
                       '_TDS_.TextLanguageProcessor.params.defaultLanguage', 'eventIconInfo'}:
        return 'preserve-exactly', 'Declared audio/icon/locale parameter default.'
    if value in {'.KEL', '.OMORI', '.AUBREY'} and context.get('callMethod') == 'replace':
        return 'preserve-exactly', 'Native resource extension replacement.'
    if value == 'save/' and context.get('callMethod') == 'join' or value == '/data/' and context.get('callMethod') == 'printLoadingError':
        return 'preserve-exactly', 'Native storage/resource path prefix.'
    if value == 'name_cursor' and row['asset'].endswith('/Omori Name Input.OMORI'):
        return 'preserve-exactly', 'Custom name-input cursor bitmap return contract.'
    if function == 'Window_Base.prototype.convertMacroText' and value == 'YANFLYMACROTESTREVERSEDOUBLESLASH':
        return 'preserve-exactly', 'Temporary native backslash-unescape sentinel.'
    if function == 'BattleManager.actionChangeSwitch' and value == 'toggle' or assignment == 'value' and value == 'auto' and row['asset'].endswith('/YEP_X_ExtMesPack1.OMORI'):
        return 'preserve-exactly', 'Native toggle/automatic-position enum.'
    if function.startswith('Window_DebugEdit.'):
        return 'preserve-exactly', 'Developer debug switch markers.'
    if assignment == 'text' and context.get('functionName') is None and row['asset'].endswith(('/YEP_X_AnimatedSVEnemies.OMORI', '/YEP_X_ExtMesPack2.OMORI', '/YEP_X_ExtMovePack1.OMORI', '/YEP_Z_PassiveCases.OMORI')):
        return 'preserve-exactly', 'Developer plugin dependency installation diagnostic.'
    if function in {'Game_Map.prototype.displayNameDimColor1', 'Game_Map.prototype.displayNameDimColor2'}:
        return 'preserve-exactly', 'Native dim-color construction component.'
    if function == 'Scene_PetRocks.prototype.checkWinConditions' and context.get('callMethod') == 'setValue' and context.get('callArguments', [])[:1] == ['825']:
        return 'preserve-exactly', 'Pet Rocks winner dispatch variable825; original opponent/player enum is consumed by event conditions.'
    if function == 'Window_Base.prototype.convertEscapeCharacters' and value == ' x':
        return 'preserve-exactly', 'Item quantity multiplier display symbol retained as original formatting.'
    if assignment == 'mapData' and context.get('propertyKey') == 'name' and row['asset'].endswith('/Omori BlackLetterMap.OMORI'):
        return 'visible', 'Area name passed to Window_OmoBlackLetterMapName when name switch is enabled.'
    if function in {'Graphics.printLoadingError', 'Graphics._createModeBox', 'Graphics.processErrorStackMessage',
        'Scene_Boot.prototype.isGameFontLoaded', 'SceneManager.checkWebGL', 'SceneManager.checkFileAccess',
        'SceneManager.initAudio', 'SceneManager.onError', 'SceneManager.catchException', 'DataManager.checkError',
        'AudioManager.checkWebAudioError', 'PluginManager.checkErrors', 'Game_Map.prototype.setup',
        'Game_Interpreter.prototype.checkOverflow', 'Scene_Boot.prototype.checkPlayerLocation',
        'Window_BattleLog.prototype.callNextMethod', 'Scene_BaseEX.prototype.callNextQueueFunction',
        'ResourceHandler.fetchWithRetry', 'Window_OmoMenuEquipStatus.prototype.refresh',
        'Scene_Battle.prototype.pushPartyMessage', 'KeyboardInput.getKeyName', 'KeyboardInput.getGamepadButtonName',
        'Window_OmoMenuOptionsSystem.prototype.getCommandHelpText', 'LanguageManager.getSystemText',
        'LanguageManager.getPluginText', 'LanguageManager.getInputName', 'LanguageManager.getDatabaseText',
        '$.getTextData', 'Window_Options.prototype.booleanStatusText', 'Game_Interpreter.prototype.getToolName'}:
        return 'visible', 'Bound player display/system error fallback or assembled interface label.'
    if assignment in {'Scene_Boot', 'Graphics', 'DataManager', 'stateMsg'}:
        return 'visible', 'Player system error/battle fallback display; controls and comparisons are separate.'
    if function == 'Window_Base.prototype.convertEscapeCharacters' and value == 'NULL ID #':
        return 'visible', 'Item lookup display fallback; retain dynamic identity outside the literal.'
    if context.get('propertyKey') == 'properties' and assignment == 'data':
        return 'preserve-exactly', 'Native tween property list; controls geometry/opacity, not text.'
    if assignment in {'name', 'data', 'param', 'line', 'icon'}:
        if assignment == 'name' and (function.startswith('StorageManager.') or 'minigame_jash' in value or function in {'Game_Interpreter.prototype.updateSingingEventBGM', 'BattleManager.actionMotionTarget'}):
            return 'preserve-exactly', 'Bound audio/storage/motion resource construction.'
        if assignment == 'param' and function.startswith(('DataManager.processLSNotetags', 'Yanfly.SetupParameters')):
            return 'preserve-exactly', 'Formula/parameter dispatch key construction.'
        if assignment == 'line' and function == 'DataManager.processAutomaticStealDebuff':
            return 'preserve-exactly-program', 'Generated mechanical debuff program fragment.'
        if assignment == 'icon' and value.startswith('\\i['):
            return 'preserve-exactly', 'Native generated icon escape prefix.'
        if assignment == 'data' and context.get('propertyKey') == 'name':
            return 'preserve-exactly', 'Tween/album section lookup name; source labels are separately catalogued.'
    if re.fullmatch(r'<(?:/?font[^>]*|/?b|br)>', value) or re.fullmatch(r'(?:\\i|\x1b[A-Za-z]+)\[(?:%\d|\d*)\]?', value):
        return 'preserve-exactly', 'Native HTML or message escape control scaffold.'
    if function.endswith('parseNoEffectEmotion') or function.endswith('parseNoStateChange'):
        return 'visible', 'Bound battle feedback template construction; comparisons remain exact.'
    if assignment == 'pronumn' and function == 'Window_BattleLog.prototype.makeCustomActionText':
        return 'visible', 'Battle message pronoun component; preserve branch and participant semantics.'
    if assignment in {'SceneManager.preferableRendererType', 'Bitmap.prototype.defaultInputIcons',
                       'Bitmap.prototype.drawAlginedKeyIcon', 'BattleManager.setPictureDisplayLayer',
                       'Input.keyMapper[65]', 'this._fileInput.type', 'numberInput.type', 'style.type', 'script.type',
                       'ysp.VideoPlayer.newVideo', 'Utils.rgbToCssColor', 'Window_DebugRange.prototype.mode',
                       'Scene_Save.prototype.mode', 'Scene_Load.prototype.mode'}:
        return 'preserve-exactly', 'Bound renderer/resource/input/DOM/scene mode contract.'
    if function.startswith(('Scene_AtlasMaker.', 'AtlasMakerContainer')):
        return 'preserve-exactly', 'Developer atlas editor schema/UI, outside game narrative and player interface.'
    if function == 'updateInfo' and row['asset'].endswith('/AudioStreaming.OMORI'):
        return 'preserve-exactly', 'Developer audio load/decode timing overlay.'
    if assignment in {'messages', 'success', 'failure'} and row['asset'].endswith(('/AudioStreaming.OMORI', '/OggOnly.OMORI')):
        return 'preserve-exactly', 'Developer audio conversion/deletion utility prompts, outside player interface.'
    if assignment in {'text', 'value2'} and (function.startswith('Window_Debug') or function == 'Window_NameEdit.prototype.charWidth' or function == 'Graphics.isFontLoaded'):
        return 'preserve-exactly', 'Developer debug markers or native glyph/font measurement probe.'
    if function.startswith('Scene_Debug.'):
        return 'preserve-exactly', 'Developer switch/variable editor help, outside player interface.'
    if assignment in {'Graphics._makeFullErrorHtml', 'Graphics._makeErrorHtml', 'Graphics'} and '<font' in value or value in {'</b></font><br>', '</font><br>'}:
        return 'preserve-exactly', 'Error renderer HTML syntax.'
    if value == 'This is a static class' or value == 'This is not a class':
        return 'preserve-exactly', 'Native non-instantiable API guard diagnostic.'
    if value.startswith('vec3 mod289('):
        return 'preserve-exactly', 'Nested GLSL Perlin noise function source.'
    if context.get('commandCode') == 45 and context.get('propertyKey') == 'parameters':
        return 'preserve-exactly-program', 'Native move-route script; complete nested AST inventoried separately before acceptance.'
    if context.get('commandCode') == 44 and context.get('propertyKey') == 'name':
        return 'preserve-exactly', 'Typed move-route sound resource name.'
    if assignment in TECH_ASSIGNMENTS or assignment in TECH_RETURNS:
        return 'preserve-exactly', 'Bound owning variable/return contract: dispatch, formula, resource, identity or input metadata.'
    if re.search(r'(?:\.style[.\[]|\.(?:fillStyle|globalCompositeOperation|textBaseline|lineJoin|fontFace|outlineColor|textColor|font|fontFamily|responseType|id|accept|panningModel)$)', assignment):
        return 'preserve-exactly', 'Native DOM/CSS/canvas/font/resource transport property.'
    if assignment.startswith(('Imported.', 'Yanfly.BEC.DefaultAction')) or re.search(r'\.(?:_loadingState|_layoutType|_dataClass|_vehicleType|_phase|_returnPhase|_activationType)$', assignment):
        return 'preserve-exactly', 'Plugin version or engine enum/action dispatch state.'
    if re.search(r'(?:Motion|LifeStealRate|LifeStealFlat|Battleback[12]Name|CursorRectBitmapName|itemTextAlign)$', assignment):
        return 'preserve-exactly', 'Owning return contract is motion, formula, resource bitmap or alignment.'
    if re.fullmatch(r'(?:#[0-9a-fA-F]{3,8}|rgba?\([\d.,\s]+\)|(?:\\[icIC]|\x1b[cCiI])\[(?:%\d|\d+)?\]|<(?:WordWrap|CENTER|SIMPLE)>|[%\d\W_]+)', value):
        return 'preserve-exactly', 'Color, native escape scaffold or punctuation-only numeric/layout formatting.'
    if assignment in TECH_TABLES or assignment.startswith(('Window_NameInput.', 'VirtualKeyboard.')):
        return 'preserve-exactly', 'Character/key mapping, name filter, identity conversion or database resource table; display text is sourced separately.'
    if re.fullmatch(r'[\w-]+\.message_\w*', value):
        return 'preserve-exactly', 'Exact catalog reference or dynamically suffixed catalog reference prefix.'
    method, argument = context.get('callMethod'), context.get('callArgumentIndex', -1)
    if method == 'push' and ('Window_BattleLog' in function or function.startswith(('BattleManager.', 'Yanfly.BEC.BattleManager'))):
        if context.get('callArguments', [])[:1] not in [["'addText'"], ['"addText"']]:
            return 'preserve-exactly', 'Battle log/action queue dispatch and control payload; display addText is handled separately.'
    if method == 'bind' and argument >= 1 and context.get('callArguments', [])[:1] in [['this'], ['window']]:
        return 'preserve-exactly', 'Bound callback dispatch/control payload; nested calls are classified independently.'
    if method == 'queue' or method == 'customEffectEval':
        return 'preserve-exactly', 'Deferred animation/effect dispatch and control payload.'
    if method == 'sformat' and value.startswith('[ARCHEIA STEAMWORKS]'):
        return 'preserve-exactly', 'Native platform diagnostic message, console consumer.'
    if method in {'parseInt', 'parseFloat', 'open', 'check'}:
        return 'preserve-exactly', 'Numeric parsing, transport or font-check syntax.'
    if method == 'format' and re.fullmatch(r'(?:Map%1\.(?:json|KEL)|file%1\.rpgsave|\\i\[%1\]%2|\x1bC\[%1\])', value):
        return 'preserve-exactly', 'Native resource or icon/control format template.'
    if method == 'addCommand':
        if argument == 0:
            return 'visible', 'Window command display label; command symbol and control arguments are separate.'
        return 'preserve-exactly', 'Window command symbol or non-display control argument.'
    if method == 'push' and context.get('callArguments', [])[:1] in [["'addText'"], ['"addText"']]:
        return ('preserve-exactly', 'Battle log dispatch symbol.') if argument == 0 else ('visible', 'Battle log message argument.')
    if method in {'queue', 'bind', 'customEffectEval', 'processStateEval', 'processCreateStealItem', 'auraStateTypeIds'}:
        if argument == 0:
            return 'preserve-exactly', 'Deferred dispatch method/effect/category identifier.'
    if method == 'getParamString' and argument == 0:
        return 'preserve-exactly', 'Plugin-parameter lookup key.'
    if method in {'replace', 'split', 'join', 'lastIndexOf'} and argument == 0:
        return 'preserve-exactly', 'Native matching/separator operand; display replacements require separate role proof.'
    if method in {'log', 'warn', 'error', 'info', 'displayError'}:
        return 'preserve-exactly', 'Developer console/error diagnostic component, retained in original form; not game narrative/interface wording.'
    if context.get('callMethod') in TECHNICAL:
        return 'preserve-exactly', 'Declared resource, lookup, input, comparison or runtime-control API argument.'
    if context.get('callMethod') in DISPLAY:
        if argument != 0:
            return 'preserve-exactly', 'Non-display argument of declared display API (alignment/control).'
        return 'visible', 'Display API first argument; exact source AST identifies the slot.'
    if row['asset'].endswith('/Custom Battle Action Text.OMORI') and context.get('functionName') == 'Window_BattleLog.prototype.makeCustomActionText':
        if assignment in {'text', 'hpDamageText', 'mpDamageText'} or context['parentType'] == 'ReturnStatement':
            return 'visible', 'Custom action message construction; preserve complete assembled expression and dynamic participants.'
    if method in {'parseNoStateChange', 'parseNoEffectEmotion'}:
        return 'visible', 'Bound GTP battle-log message component; preserve actual template and dynamic participants.'
    if assignment.startswith('_TDS_.ActiveChainSkills.params.inputData.') or assignment == '_TDS_.ActiveChainSkills.params.chainTitle':
        return 'visible', 'Active Chain Skills display default; configured parameter is separately inventoried.'
    if value == 'use strict':
        return 'preserve-exactly', 'JavaScript directive.'
    if re.fullmatch(r'[-+]?\d+(?:\.\d+)?|true|false|undefined|null', value):
        return 'preserve-exactly', 'Numeric/boolean/null/undefined control literal.'
    if any(term in value for term in ('uniform ', 'varying ', 'attribute ', 'void main(')):
        return 'preserve-exactly', 'GLSL program source.'
    return 'needs-role-review', 'Consumer/argument/return or encoded subformat requires explicit binding.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ast')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    from pathlib import Path
    output, input_path = Path(args.output), Path(args.ast)
    if output.exists():
        raise ValueError('Preserve prior role evidence')
    ast = strict_json(input_path.read_bytes())
    rows, counts = [], Counter()
    for original in ast['strings']:
        row = dict(original)
        row['role'], row['reason'] = classify(row)
        counts[row['role']] += 1
        rows.append(row)
    save_json(output, {'schemaVersion': 1, 'inputAstRawSha256': sha(input_path.read_bytes()),
                       'recipeRawSha256': sha(Path(__file__).read_bytes()), 'roles': dict(counts), 'strings': rows,
                       'sourceGate': 'needs-review', 'runtime': 'not-run',
                       'limits': ['Display candidates still require exact argument-role and mixed-format checks.',
                                  'A classified literal is not a translated or semantically audited unit.']})
    print(dict(counts))


if __name__ == '__main__':
    main()
