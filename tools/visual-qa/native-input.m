#import <AppKit/AppKit.h>
#import <CoreGraphics/CoreGraphics.h>
int main(int argc,const char **argv){@autoreleasepool{
 if(argc!=3)return 64;
 NSString *action=@(argv[1]); int value=atoi(argv[2]);
 if([action isEqual:@"key"]){
  if(value!=6&&value!=7&&value!=36&&value!=125&&value!=126)return 65;
  CGEventRef d=CGEventCreateKeyboardEvent(NULL,value,true),u=CGEventCreateKeyboardEvent(NULL,value,false);
  CGEventPost(kCGHIDEventTap,d);usleep(80000);CGEventPost(kCGHIDEventTap,u);CFRelease(d);CFRelease(u);
 }else if([action isEqual:@"focus"]){
  NSRunningApplication *a=[NSRunningApplication runningApplicationWithProcessIdentifier:value];
  if(![a.executableURL.path hasPrefix:@"/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/"])return 66;
  if(![a activateWithOptions:NSApplicationActivateAllWindows|NSApplicationActivateIgnoringOtherApps])return 67;
 }else return 68;
 return 0;
}}
