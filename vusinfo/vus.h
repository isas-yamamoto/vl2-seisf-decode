/**
 *  @file      vus.h
 *  @brief     Header file of Viking Seismic Data (VUS Tapes)
 *             This file contains VUS information
 *  @author    Yukio Yamamoto
 *  @date      November 25, 2010
 */

#ifndef __VUS_H__
#define __VUS_H__

/*
 * @see ftp://ftp.ig.utexas.edu/pub/PSE/catsrepts/TechRept118.pdf
 * University of Texas Institute for Geophysics Technical Report No.118,
 * Catalog of Lunar Seismic Data from Apollo Passive Seismic Expreiment
 * on 8-mm Video Cassette (Exabyte) Tapes" p.11 Viking Tape
 */

/*
 * Viking Tape
 *  - One file for each original 7-track Viking tape
 *  - Record size: 1000 bytes for headers; 10752, 10764 or 11250 bytes for data; variable-
 *    length format
 *  - Each file contains multiple subgroups,each of which represents a copy of a single file
 *    on the original 7-track tape (no end-of-file mark between subgroups). Each subgroup
 *    consists of a 1000-byte header record followed by data records.
 */

/*
 *  - Header format:
 *  Bytes      Information (16-bit integers except for bytes 3-8)
 *  --------   ---------------------------------------------------
 *  1-2        5 to identify Viking tape
 *  3-8        original 7-track tape label
 *  9-10       file number on the original tape
 *  11-12      length,in bytes,of each data record to follow
 *  13-1000    filled with zeroes
 */

/*
 * - Data format:  Each 6-bit byte of the original 7-track data coccupies the 6 lsb (bits 2-7)
 *   of an 8-bit byte in data record with 2 msb (bits 0-1) filled with zeroes. If the original
 *   record length is shorter than the available record length, the remaining bytes are filled
 *   with FFh (all bits set). See appropriate NASA Viking Project documents for data
 *   format of original 7-track tapes.
 */

/*
 * - The tape ends with double end-of-file marks.
 */

#define SIZE_RECORD_HEADER 1000
#define SIZE_RECORD_DATA   11250
#define SIZE_BUFFER (SIZE_RECORD_HEADER+SIZE_RECORD_DATA)

/*
 * On Viking Lander 2 mission, 
 *   1 byte  =  6 bits
 *   1 word  =  6 bytes (36 bits)
 *   1 frame = 75 words (2700 bits)
 *
 * For the avoidance of confusion, the following expression is used:
 *   6-bit byte  (instead of 1 byte)
 *   36-bit word (instead of 1 word)
 */
#define BITS_PER_BYTE    6
#define BYTE_PER_WORD    6
#define WORDS_PER_FRAME  75

#define SIZE_EVENT_DATA  53
#define SIZE_NORMAL_DATA 83

#define BITS_PER_WORD    (BITS_PER_BYTE * BYTE_PER_WORD)
#define BITS_PER_FRAME   (BITS_PER_WORD * WORDS_PER_FRAME)
#define BYTE_PER_FRAME   (BYTE_PER_WORD * WORDS_PER_FRAME)


#define MODE_NORMAL  0
#define MODE_HIGH    1
#define MODE_EVENT   2
#define MODE_NORMAL2 3

typedef struct tag_vus_header {
  int id;        /* 5 to identify Viking tape                     */
  char label[7]; /* original 7-track tape label                   */
  int file_no;   /* file number on the original tape              */
  int length;    /* length,in bytes,of each data record to follow */
} vus_header;

typedef struct tag_seisf_header {
  int doy;
  int year;
} seisf_header;

typedef struct tag_frame_header {
  int gcsc;
  int sol, hour, min, csec;
  int cmd_status;
  int change_code;
} frame_header;

typedef struct tag_command_status {
  /**
   * @brief Mode of operation of seismometer
   *           0 ... NORMAL
   *           1 ... HIGH
   *           2 ... EVENT
   *           3 ... not dtermined
   */
  int mode;
  
  /**
   * @brief Vertical (x-component) attenuation
   *           0 ... 18DB
   *           1 ...  0DB
   *           2 ... 30DB
   *           3 ... 12DB
   *           4 ... 24DB
   *           5 ...  6DB
   *           6 ... 36DB
   *           7 ... 18DB
   */
  int vatten;

  /**
   * @breif Horizontal (y- and z-component) attenuation
   *           0 ... 18DB
   *           1 ...  0DB
   *           2 ... 30DB
   *           3 ... 12DB
   *           4 ... 24DB
   *           5 ...  6DB
   *           6 ... 36DB
   *           7 ... 18DB
   */
  int hatten;

  /**
   * @breif Trigger level. Signal must rise above backgrouind by this factor
   *        trigger into EVENT mode. Has no meaning if trigger is not set.
   *           0 ... X12
   *           1 ...  X8
   *           2 ... X20
   *           3 ... X12
   *           4 ... X16
   *           5 ... X12
   *           6 ...  X4
   *           7 ... ' '
   */
  int tlevel;
  
  /**
   * @breif Rollover point for the hi-pass filter. Has no meaning for EVENT
   *        mode (filter cannot be used in this mode).
   *           0 ... 2.HZ
   *           1 ... .5HZ
   *           2 ... 1.HZ
   *           3 ... 4.HZ
   */
  int filt;
  
  /**
   * @brief Indicates status of filter range. 
   *           0 ... STEP
   *           1 ... FIX
   *         'FIX' indicates IFILT value holds for entire buffer.
   *         'STEP' (only allowable in NORMAL mode) indicates that first 8 data
   *         samples are at IFILT setting; filter then cycles throught all
   *         possible values in the sense .5HZ->1.HZ->2.HZ->4.HZ->.5HZ,etc. at
   *         8 data sample intervals. Has no meaning in EVENT mode.
   */
  int fmode;
  
  /**
   * @brief Trigger status of x-component (any or all of triggers may be enabled
   *        at any time.
   *           0 ... XON
   *           1 ... XOFF
   */
  int xtrig;
  
  /**
   * @brief Trigger status of y-component (any or all of triggers may be enabled
   *        at any time.
   *           0 ... YON
   *           1 ... YOFF
   */
  int ytrig;
  
  /**
   * @brief Trigger status of z-component (any or all of triggers may be enabled
   *        at any time.
   *           0 ... ZON
   *           1 ... ZOFF
   */
  int ztrig;
  
  /**
   * @breif Calibration status. Only has meaning in high data rate.
   *           0 ... CALON
   *           1 ... CALOFF
   *           2 ... CALOFF
   *           3 ... CALON
   */
  int cal;
  
} command_status;

void vus_frame(unsigned char* frame);

#endif
