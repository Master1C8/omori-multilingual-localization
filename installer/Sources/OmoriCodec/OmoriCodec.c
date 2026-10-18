#include "OmoriCodec.h"
#include <zlib.h>
#include <CommonCrypto/CommonCryptor.h>
int omori_gunzip(const void *input,size_t n,void *output,size_t cap) {
    z_stream s={0}; s.next_in=(Bytef *)input;s.avail_in=(uInt)n;s.next_out=output;s.avail_out=(uInt)cap;
    if(inflateInit2(&s,31)!=Z_OK)return 1;
    int r=inflate(&s,Z_FINISH);int ok=(r==Z_STREAM_END && s.total_out==cap && s.avail_in==0);inflateEnd(&s);return !ok;
}
int omori_ctr(const void *input,size_t n,const void *iv,void *output) {
    static const char key[]="6bdb2e585882fbd48826ef9cffd4c511";
    CCCryptorRef c=0;size_t done=0;
    int r=CCCryptorCreateWithMode(kCCEncrypt,kCCModeCTR,kCCAlgorithmAES,ccNoPadding,iv,key,32,0,0,0,kCCModeOptionCTR_BE,&c);
    if(r)return r;
    r=CCCryptorUpdate(c,input,n,output,n,&done);CCCryptorRelease(c);return r?r:(done!=n);
}
