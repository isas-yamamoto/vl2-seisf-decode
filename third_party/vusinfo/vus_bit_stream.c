
/**
 *  @file      vus_bit_stream.c
 *  @brief     Bit-stream functions for Viking Seismic Data (VUS Tapes)
 *  @author    Yukio Yamamoto
 *  @date      September 30, 2013
 */

#include "vus.h"
#include "vus_utils.h"
#include "vus_bit_stream.h"

void make_bit_stream(const unsigned char* frame, unsigned char* bits) {
  int word, bit_offset;
  int i;
  for(word=1; word<=WORDS_PER_FRAME; ++word) {
    for(i=0; i<BITS_PER_WORD; ++i) {
      bit_offset = (word-1) * BITS_PER_WORD + ((i<18) ? (17-i) : (35-i+18));
      bits[bit_offset] = get_vus_data(frame, word,i,i);
    }
  }
}

int search_change_code(const unsigned char* bits, int* founds) {
  int change_code[] = {0,0,0, 0,1,1, 1,0,1, 1,0,0, 1,0,1};
  int i, j;
  int count = 0;
  for(i=(19*BITS_PER_WORD); i<BITS_PER_FRAME-SIZE_CHANGE_CODE_BITS-SIZE_SOURCE_CODE_BITS; i++) {
    for(j=0; j<SIZE_CHANGE_CODE_BITS; ++j) {
      if (change_code[j] != bits[i+j]) {
	break;
      }
    }
    if (j == SIZE_CHANGE_CODE_BITS) { // found
      founds[count] = i;
      count++;
    }
  }
  return count;
}

int get_int_from_bit_stream(const unsigned char* bits, int offset, int len, int sign) {
  int i;
  int ret = 0;
  
  for(i=0; i<len; ++i) {
    ret <<= 1;
    ret |= bits[offset+len-1-i];
  }
  if (sign && bits[offset+len-1]) {
    ret -= 1 << len;
  }
  return ret;
}

int get_lsb_bit_offset(const unsigned char* frame, int word) {
  return (word - 1) * BITS_PER_WORD;
}

int extract_data_from_bit_stream(const unsigned char* bits, seismic_data* data) {
  int gcsc_start_bit_offset[MAX_CHANGES+1];
  int change_code_offsets[MAX_CHANGES];
  int bit_limits[MAX_CHANGES+1];
  int gcsc_loop = 1;
  int count;
  int gcsc_index;
  int data_index;
  int i;
  
  // make GCSC pointer due to multiple data in a frame
  gcsc_start_bit_offset[0] = get_lsb_bit_offset(bits, 19);
  count = search_change_code(bits, change_code_offsets);
  if (count > 0) {
    for(i=0; i<count; ++i) {
      gcsc_start_bit_offset[i+1] = change_code_offsets[i] +  SIZE_CHANGE_CODE_BITS + SIZE_SOURCE_CODE_BITS;
      bit_limits[i] = change_code_offsets[i] - (3 * SIZE_AMPLITUDE);
    }
    gcsc_loop += count;
  }
  gcsc_start_bit_offset[gcsc_loop] = WORDS_PER_FRAME * BITS_PER_WORD;
  bit_limits[gcsc_loop-1] = WORDS_PER_FRAME * BITS_PER_WORD - (3 * SIZE_AMPLITUDE);
  
  for(gcsc_index=0; gcsc_index < gcsc_loop; ++gcsc_index) {
    int offset = gcsc_start_bit_offset[gcsc_index];
    if (gcsc_index == 0) {
      data[gcsc_index].gcsc = get_int_from_bit_stream(bits, offset, 23, FALSE);
      data[gcsc_index].gcsc <<= 1;
      offset += 23;
    } else {
      data[gcsc_index].gcsc = get_int_from_bit_stream(bits, offset, 24, FALSE);
      offset += 24;
    }
    
    data[gcsc_index].cmd_status = get_int_from_bit_stream(bits, offset, SIZE_COMMAND_STATUS, FALSE);
    offset += SIZE_COMMAND_STATUS;
    data[gcsc_index].cs = extract_command_status(data[gcsc_index].cmd_status);	    
    
    if (gcsc_index == 0) {
      data[gcsc_index].change_code = get_int_from_bit_stream(bits, offset, 8, FALSE);
      offset += 8;
    }
    
    // extract seismic data
    data_index = 0;
    while(offset<bit_limits[gcsc_index]) {
      for(i=0; i<3; ++i) {
	data[gcsc_index].amp[i][data_index] = get_int_from_bit_stream(bits, offset, SIZE_AMPLITUDE, TRUE);
	offset += SIZE_AMPLITUDE;
	if (data[gcsc_index].cs.mode == MODE_EVENT) {
	  data[gcsc_index].axis[i][data_index] = get_int_from_bit_stream(bits, offset, SIZE_AXIS_CROSSING, FALSE);
	  offset += SIZE_AXIS_CROSSING;
	}
      }
      ++data_index;
    }
    data[gcsc_index].ndata = data_index;
  }
  return gcsc_loop;
}
