#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
int main(int argc,const char **argv){@autoreleasepool{
 if(argc!=2)return 64;pid_t pid=atoi(argv[1]);
 NSRunningApplication *app=[NSRunningApplication runningApplicationWithProcessIdentifier:pid];
 if(![app.executableURL.path hasPrefix:@"/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/"])return 65;
 NSArray *all=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionAll|kCGWindowListExcludeDesktopElements,kCGNullWindowID));
 NSMutableArray *owned=[NSMutableArray array];
 for(NSDictionary *w in all)if([w[(id)kCGWindowOwnerPID] intValue]==pid && [w[(id)kCGWindowLayer] intValue]==0)[owned addObject:w];
 NSData *data=[NSJSONSerialization dataWithJSONObject:owned options:NSJSONWritingPrettyPrinted error:nil];
 fwrite(data.bytes,1,data.length,stdout);return 0;
}}
