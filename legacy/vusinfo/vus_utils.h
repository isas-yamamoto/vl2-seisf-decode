/**
 *  @file      vus_utils.h
 *  @brief     Header file of utilities for Viking Seismic Data (VUS Tapes)
 *  @author    Yukio Yamamoto
 *  @date      November 25, 2010
 */
#ifndef __VUS_UTILS_H__
#define __VUS_UTILS_H__

#ifndef TRUE
#define TRUE 1
#endif

#ifndef FALSE
#define FALSE 0
#endif

#define VUS_FRAME_TYPE_NORMAL  0x0000
#define VUS_FRAME_TYPE_ALL_ONE 0x0001

#define SOL_CSEC 8877525

/**
 * @brief Check scrambled VUS header
 *
 * @param record Data record containing 25 frames of data.
 * @return check_vus_seis_header() returns TRUE if the header is in a valid
 * format, FALSE otherwise.
 */
int check_vus_seis_header(unsigned char* record);

/**
 * @brief check unscrambled VUS header
 *
 * @param record Data record containing 25 frames of data.
 * @return check_vus_useis_header() returns TRUE if the header is in a valid
 * format, FALSE otherwise.
 */
int check_vus_useis_header(unsigned char* record);

/**
 * @brief Get VUS frame type
 *
 * @param record Data record containing 25 frames of data.
 * @return get_vus_frame_type() returns the type of VUS frame.
 */
int get_vus_frame_type(unsigned char* record, int length);

/**
 * @brief dump VUS frame in 75 36-bit words in octal
 *
 * @param frame   Frame (logical record) containing 75 36-bit words
 *                (450 6-bit bytes) long.
 * @param length  Dump length of the frame
 */
void vus_6bit_dump(unsigned char* frame, int length);

/**
 * @brief dump VUS frame in 
 *
 * @param frame   Frame (logical record) containing 75 36-bit words
 *                (450 6-bit bytes) long.
 * @param length  Dump length of the frame
 */
void vus_8bit_dump(unsigned char* frame, int length);

/**
 * @brief dump VUS frame in 75 36-bit words in hex for BCD debug
 *
 * @param frame   Frame (logical record) containing 75 36-bit words
 *                (450 6-bit bytes) long.
 * @param length  Dump length of the frame
 */
void vus_6bit_hex_dump(unsigned char* frame, int length);

/**
 * @brief get EXBYTE header
 *
 * @param data    Data including EXBYTE header
 */
vus_header get_exb_header(unsigned char* data);

/**
 * @brief print EXBYTE header
 *
 * @param data    Data including EXBYTE header
 */
void print_exb_header(unsigned char* data);

/**
 * @brief print Record header
 *
 * @param cs      Command Status
 * @param verbose verbose mode flag
 */
void print_command_status(const command_status* cs, int verbose);

/**
 * @brief get VUS data
 * @param frame  Frame (logical record) containing 75 36-bit words
 *               (450 6-bit bites) long.
 * @param word   Offset of 36-bit words
 * @param start  Start bit of the word
 * @param end    End bit of the word
 *
 * @return the data extracted.
 */
int get_vus_data(const unsigned char* frame, int word, int start, int end);

/**
 * @brief convert GCSC to SOL/LLT
 *
 * @param[in]  gcsc    24-bit GCSC count
 * @param[in]  sol_est calendar day of the year 1976
 * @param[out] sol     solar time of Mars
 * @param[out] hour    hour of LLT
 * @param[out] min     min of LLT
 * @param[out] csec    centicecond of LLT
 *
 */
void gcsc2llt(unsigned int gcsc, int sol_est, int* sol, int *hour, int *min, int *csec);

/**
 * @brief convert from LLT to GCSC
 *
 * @param[in]  sol     solar time of Mars
 * @param[in]  hour    hour of LLT
 * @param[in]  min     min of LLT
 * @param[in]  csec    centicecond of LLT
 * @return llt2gcsc() returns GCSC using LLT.
 */
int llt2gcsc(int sol, int hour, int min, int csec);

/**
 * @brief get the sequential day number starting with day 1 on January 1st, 1976
 *
 * @param[in]  year    year
 * @param[in]  doy     day of year
 *
 * @return the sequential day number starting with day 1 on January 1st, 1976.
 */
int get_sequential_days_from_1976(int year, int doy);

/**
 *
 * @brief convert BCD string to integer
 *
 * @param[in]  bcd     BCD string
 * @return bcd2int() returns integer value corresponding to BCD code.
 *
 */
int bcd2int(int bcd);

/**
 * @brief Convert from command status to record header
 *
 * @param cmd_status command status
 * @return extract_command_status() returns record_header structure.
 */
command_status extract_command_status(int cmd_status);

/**
 * @brief Create value from bit stream
 *
 * @param bits    bit-stream array of frame data
 * @param index   start point of the bit-stream
 * @param len     length of bits
 */
int bits2val(unsigned char* bits, int index, int len);

#endif
