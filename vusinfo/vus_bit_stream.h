/**
 *  @file      vus_bit_stream.h
 *  @brief     Bit-stream functions for Viking Seismic Data (VUS Tapes)
 *  @author    Yukio Yamamoto
 *  @date      September 30, 2013
 */
#ifndef __VUS_BIT_STREAM_H__
#define __VUS_BIT_STREAM_H__

#define SIZE_COMMAND_STATUS 22
#define SIZE_CHANGE_CODE_BITS 15
#define SIZE_SOURCE_CODE_BITS 5
#define SIZE_AMPLITUDE 8
#define SIZE_AXIS_CROSSING 5
#define MAX_CHANGES (int)(2048/SIZE_CHANGE_CODE_BITS)

typedef struct tag_seismic_data {
  int gcsc;
  int cmd_status;
  int change_code;
  int amp[3][SIZE_NORMAL_DATA];
  int axis[3][SIZE_NORMAL_DATA];
  int ndata;
  command_status cs;
} seismic_data;

/**
 * @brief Make bit stream from 25 frames of data
 *
 * @param[in]  record  Data record containing 25 frames of data
 * @param[out] bits    bitstream
 */
void make_bit_stream(const unsigned char* frame, unsigned char* bits);

/**
 * @brief Search change code string 101001101110000
 *
 * @param[in]  bits    bitstream
 * @param[out] list    list of bit offsets at found
 * @return search_change_code_string() return the count of found.
 */
int search_change_code(const unsigned char* bits, int* founds);

/**
 * @brief get integer value from bitstream
 *
 * @param[in]  bits    bitstream
 * @param[in]  offset  offset of bits
 * @param[in]  len     length of bits
 * @param[in]  sign    sign
 * @return get_int_from_bit_stream() returns integer value from bitstream.
 */
int get_int_from_bit_stream(const unsigned char* bits, int offset, int len, int sign);

/**
 * @brief get the bit offset for LSB in a word
 *
 * @param[in]  bits    bitstream
 * @param[in]  word    word
 * @return get_lsb_bit_offset() returns bit offset in a word.
 */
int get_lsb_bit_offset(const unsigned char* frame, int word);

/**
 * @brief extract data from bitstream
 *
 * @param[in]  bits    bitstream
 * @param[out] data    seismic data structure
 * @return extract_data_from_bit_stream()  returns the number of seismic data structure.
 */
int extract_data_from_bit_stream(const unsigned char* bits, seismic_data* data);
#endif
