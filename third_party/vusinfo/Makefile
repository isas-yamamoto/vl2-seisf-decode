all: vusinfo

CC=gcc
CFLAGS=-Wall -g -O2
LDFLAGS=

.c.o:
	$(CC) $(CFLAGS) -c -o $@ $< 

vusinfo: vusinfo.o vus_utils.o vus_bit_stream.o
	$(CC) -o $@ $^ $(LDFLAGS)

.PHONIX: clean
clean:
	$(RM) vusinfo *.o
