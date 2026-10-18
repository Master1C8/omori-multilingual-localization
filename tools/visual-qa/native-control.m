#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
#import <Carbon/Carbon.h>
// The pinned GTP renderer wraps Graphics.frameCount modulo1024.
static long long consumedFrames(long long now,long long before){return ((now-before)%1024+1024)%1024;}
static BOOL consumedKey(long long now,long long before,BOOL pressed,BOOL changedScene){return (consumedFrames(now,before)>=2&&pressed)||changedScene;}
static BOOL inputUpdateProof(NSDictionary*s,NSDictionary*event,long long initialSerial){id p=s[@"inputConsumption"];return [p isKindOfClass:NSDictionary.class]&&[p[@"keyCode"] intValue]==[event[@"keyCode"] intValue]&&[p[@"keydownTime"] longLongValue]==[event[@"time"] longLongValue]&&[p[@"updateSerial"] longLongValue]>initialSerial;}
static BOOL acknowledgedSample(NSDictionary*s,NSDictionary*event,NSDictionary*initial,NSString*name){if(![s isKindOfClass:NSDictionary.class]||![s[@"scene"] isKindOfClass:NSString.class])return NO;BOOL changed=![s[@"scene"] isEqual:initial[@"scene"]];if(initial[@"inputUpdateSerial"]!=nil)return inputUpdateProof(s,event,[initial[@"inputUpdateSerial"] longLongValue])||changed;return consumedKey([s[@"frame"] longLongValue],[event[@"frame"] longLongValue],[s[@"input"][name] boolValue],changed);}
int main(int argc,const char**argv){@autoreleasepool{
 if(argc==2&&strcmp(argv[1],"--test-ack")==0){
  if(consumedKey(1023,1022,YES,NO)||consumedKey(0,1023,YES,NO)||!consumedKey(1,1023,YES,NO)||!consumedKey(0,1022,YES,NO)||consumedKey(500,500,YES,NO)||consumedKey(503,500,NO,NO)||!consumedKey(0,900,NO,YES))return 70;
  NSDictionary*e=@{@"keyCode":@90,@"time":@1000};
  NSDictionary*s=@{@"inputConsumption":@{@"keyCode":@90,@"keydownTime":@1000,@"updateSerial":@9}};
  if(!inputUpdateProof(s,e,8)||inputUpdateProof(s,e,9)||inputUpdateProof(s,@{@"keyCode":@88,@"time":@1000},8)||inputUpdateProof(s,@{@"keyCode":@90,@"time":@1001},8)||inputUpdateProof(@{},e,8))return 71;
  NSDictionary*initial=@{@"scene":@"Scene_Map",@"inputUpdateSerial":@8};
  NSDictionary*domOnly=@{@"scene":@"Scene_Map",@"frame":@99,@"input":@{@"ok":@YES},@"inputUpdateSerial":@9};
  NSMutableDictionary*sample=[domOnly mutableCopy];sample[@"inputConsumption"]=s[@"inputConsumption"];
  if(acknowledgedSample(domOnly,e,initial,@"ok")||!acknowledgedSample(sample,e,initial,@"ok")||acknowledgedSample(sample,@{@"keyCode":@88,@"time":@1000},initial,@"ok"))return 72;
  NSMutableDictionary*pending=[domOnly mutableCopy];pending[@"inputConsumption"]=NSNull.null;
  if(inputUpdateProof(pending,e,8)||acknowledgedSample(pending,e,initial,@"ok")||acknowledgedSample(nil,e,initial,@"ok"))return 73;
  puts("PASS modulo1024 frames and fresh matching input-update proof; stale/wrong-key/wrong-event/DOM-only evidence rejected.");return 0;
 }
 if(argc<3)return 64;pid_t pid=atoi(argv[1]);NSString *action=@(argv[2]);NSRunningApplication*a=[NSRunningApplication runningApplicationWithProcessIdentifier:pid];
 if(![a.executableURL.path hasPrefix:@"/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/"])return 65;
 if([action isEqual:@"focus"]){
  [a unhide];[a activateWithOptions:NSApplicationActivateAllWindows];
  AXUIElementRef app=AXUIElementCreateApplication(pid);
  AXError front=AXUIElementSetAttributeValue(app,kAXFrontmostAttribute,kCFBooleanTrue);
  CFTypeRef windows=NULL;
  if(AXUIElementCopyAttributeValue(app,kAXWindowsAttribute,&windows)==kAXErrorSuccess && CFGetTypeID(windows)==CFArrayGetTypeID()){
   CFArrayRef list=(CFArrayRef)windows;
   if(CFArrayGetCount(list)>0){AXUIElementRef win=(AXUIElementRef)CFArrayGetValueAtIndex(list,0);AXUIElementSetAttributeValue(win,kAXMinimizedAttribute,kCFBooleanFalse);AXUIElementPerformAction(win,kAXRaiseAction);}
   CFRelease(windows);
  }
  for(int n=0;n<50;n++){
   CFRunLoopRunInMode(kCFRunLoopDefaultMode,.1,false);
   CFTypeRef actual=NULL;AXUIElementCopyAttributeValue(app,kAXFrontmostAttribute,&actual);
   BOOL focused=actual && CFEqual(actual,kCFBooleanTrue);if(actual)CFRelease(actual);
   if(focused && NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier==pid)break;
  }
  CFRelease(app);
 }
 BOOL acked=NO;NSDictionary *ackEvidence=nil;
 if([action isEqual:@"key"]||[action isEqual:@"keydown"]||[action isEqual:@"keyup"]||[action isEqual:@"ackkey"]){BOOL ack=[action isEqual:@"ackkey"];if(argc!=(ack?5:4))return 66;int k=atoi(argv[3]);if(k!=6&&k!=7&&k!=123&&k!=124&&k!=125&&k!=126)return 67;
  CGEventSourceRef source=CGEventSourceCreate(kCGEventSourceStatePrivate);
  CGEventRef down=CGEventCreateKeyboardEvent(source,k,true),up=CGEventCreateKeyboardEvent(source,k,false);
  CGEventSetFlags(down,0);CGEventSetFlags(up,0);
  if(k==6){UniChar z='z';CGEventKeyboardSetUnicodeString(down,1,&z);CGEventKeyboardSetUnicodeString(up,1,&z);}
  double start=NSDate.date.timeIntervalSince1970*1000;
  NSData *initialRaw=ack?[NSData dataWithContentsOfFile:@(argv[4])]:nil;
  NSDictionary *initial=initialRaw?[NSJSONSerialization JSONObjectWithData:initialRaw options:0 error:nil]:nil;
  if(![action isEqual:@"keyup"])CGEventPostToPid(pid,down);
  @try {
  if(ack){
   int code=k==6?90:k==7?88:k==123?37:k==124?39:k==125?40:38;
   NSString *name=k==6?@"ok":k==7?@"escape":k==123?@"left":k==124?@"right":k==125?@"down":@"up";
   for(int n=0;n<500;n++){
    usleep(10000);NSData *raw=[NSData dataWithContentsOfFile:@(argv[4])];
    NSDictionary *s=raw?[NSJSONSerialization JSONObjectWithData:raw options:0 error:nil]:nil;
    for(NSDictionary *e in s[@"events"]){
     BOOL sampled=inputUpdateProof(s,e,[initial[@"inputUpdateSerial"] longLongValue]);
     BOOL consumed=acknowledgedSample(s,e,initial,name);
     if([e[@"type"] isEqual:@"keydown"]&&[e[@"keyCode"] intValue]==code&&[e[@"time"] doubleValue]>=start-5&&consumed){acked=YES;ackEvidence=@{@"keydown":e,@"consumedFrame":s[@"frame"],@"elapsedFramesModulo1024":@(consumedFrames([s[@"frame"] longLongValue],[e[@"frame"] longLongValue])),@"method":sampled?@"native-input-update":@"frame-or-scene",@"inputUpdateSerial":s[@"inputUpdateSerial"]?:@0};break;}
    }
    if(acked)break;
   }
  }
  if([action isEqual:@"key"])usleep(150000);
  } @finally {
  if(![action isEqual:@"keydown"])CGEventPostToPid(pid,up);
  CFRelease(down);CFRelease(up);CFRelease(source);
  }
 }
 TISInputSourceRef input=TISCopyCurrentKeyboardInputSource();NSString*layout=(__bridge NSString*)TISGetInputSourceProperty(input,kTISPropertyInputSourceID);
 NSMutableDictionary*state=[@{@"targetPid":@(pid),@"frontmostPid":@(NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier),@"targetActive":@(a.active),@"inputSource":layout?:@"unknown",@"accessibility":@(AXIsProcessTrusted()),@"eventFlags":@(CGEventSourceFlagsState(kCGEventSourceStateCombinedSessionState))} mutableCopy];
 if([action isEqual:@"ackkey"]){state[@"acknowledged"]=@(acked);if(ackEvidence)state[@"ackEvidence"]=ackEvidence;}
 NSData*d=[NSJSONSerialization dataWithJSONObject:state options:0 error:NULL];fwrite(d.bytes,1,d.length,stdout);puts("");CFRelease(input);return [action isEqual:@"ackkey"]&&!acked?68:0;
}}
