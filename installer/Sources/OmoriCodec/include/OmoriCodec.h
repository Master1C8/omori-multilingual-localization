#include <stddef.h>
int omori_gunzip(const void *input, size_t inputLength, void *output, size_t outputLength);
int omori_ctr(const void *input, size_t length, const void *iv, void *output);
