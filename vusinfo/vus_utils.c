/**
 *  @file      vus_utils.c
 *  @brief     utilities for Viking Seismic Data (VUS Tapes)
 *             This file contains utility to deal with Viking Seismic Data.
 *  @author    Yukio Yamamoto
 *  @date      November 25, 2010
 */

#include <stdio.h>
#include "vus.h"
#include "vus_utils.h"

int check_vus_seis_header(unsigned char* record) {
  if (record[0] == 0x00 && record[1] == 0x05 &&
      record[2] == 0x44 && record[3] == 0x4c && record[4] == 0x54) { /* DLT */
    return TRUE;
  }
  return FALSE;
}

int check_vus_useis_header(unsigned char* record) {
  if (record[0] == 0x00 && record[1] == 0x05 &&
      record[2] == 0x56 && record[3] == 0x55 && record[4] == 0x53) { /* VUS */
    return TRUE;
  }
  return FALSE;
}

int get_vus_frame_type(unsigned char* record, int length) {
  int i;
  for(i=0; i<length && record[i] == 0x09; ++i) ;
  return (i == length) ? VUS_FRAME_TYPE_ALL_ONE : VUS_FRAME_TYPE_NORMAL;
}

void vus_6bit_dump(unsigned char* frame, int length) {
  int i;
  int line=1;
  for(i=0; i<length; ++i) {
    
    if(i%54==0) {
      printf("%03d ", line++);
    }
    
    if(i%6==0) {
      putchar(' ');
    }
    
    printf("%d%d", frame[i]>>3, frame[i]&7);

    if(i%54==53) {
      putchar('\n');
    }
    
  }
  putchar('\n');
}

void vus_8bit_dump(unsigned char* frame, int length) {
  int i;
  
  for(i=0; i<length; ++i) {
    
    if(i%16==0) {
      printf("%08X ", i);
    }
    
    if(i%16==8) {
      putchar(' ');
    }
    
    printf("%02X", frame[i]);
    
    if(i%16==15) {
      putchar('\n');
    }
  }
  putchar('\n');
}

void vus_6bit_hex_dump(unsigned char* frame, int length) {
  int i;
  int line=1;
  int val=0;
  for(i=0; i<length; ++i) {
    
    if(i%54==0) {
      printf("%03d ", line++);
    }
    
    if(i%6==0) {
      putchar(' ');
    }

    val <<= 3;
    val += (frame[i]>>3);
    val <<= 3;
    val += (frame[i]&7);
    
    if(i%2==1) {
      printf("%03X", val);
      val = 0;
    }
    
    if(i%54==53) {
      putchar('\n');
    }
    
  }
  putchar('\n');
}

vus_header get_exb_header(unsigned char* data) {
  int i;
  vus_header vh;

  vh.id = data[0];
  vh.id = (vh.id << 8) + data[1];

  for(i=2; i<8; ++i) {
    vh.label[i-2] = data[i];
  }
  vh.label[i-2] = '\0';

  vh.file_no = data[8];
  vh.file_no = (vh.file_no << 8) + data[9];

  vh.length = data[10];
  vh.length = (vh.length << 8) + data[11];
  
  return vh;
}

void print_exb_header(unsigned char* data) {
  vus_header vh = get_exb_header(data);

  printf("5 to identify Viking tape ... %d\n", vh.id);
  printf("original 7-track tape label ... %s\n", vh.label);
  printf("file number on the original tape ... %d\n", vh.file_no);
  printf("length,in bytes,of each data record to follow ... %d\n", vh.length);
}

int get_vus_data(const unsigned char* frame, int word, int start, int end) {
  int i;
  int byte_offset, bit_offset;
  int ret;
  const unsigned char* p = frame + (word-1) * 6;
  
  ret = 0;
  for(i=start; i<=end; ++i) {
    byte_offset = (int)(i / 6);
    bit_offset = i % 6;
    ret = ret << 1;
    ret |= (*(p+byte_offset) >> (5-bit_offset)) & 0x01;
  }

  return ret;
}

int bits2val(unsigned char* bits, int index, int len) {
  int val = 0;
  int i;
  for(i=0; i<len; ++i) {
    val += (bits[index+i] << i);
  }
  return val;
}

void gcsc2llt(unsigned int gcsc, int doy, int* sol, int *hour, int *min, int *csec) {
  int i, ige;
  double ge16, t, tr;
  const double lo0 = 2344400;
  const int maxg[] = {
    11242789,36555517,67108864,93338597,134217728,201326592,320000000
  };
  const double cg[] = {
    8.4276E-6,8.99984E-6,1.01318E-5,1.81923E-5,1.38394E-5,1.36977E-5,1.47743E-5
  };
  const int lo[] = {
    0,103,765,9420,2919,2614,6082
  };
  
  ige = (doy-232)*540000-gcsc;
  ige &= 0xff000000;
  ige += gcsc;
  for (i=0; i<7; ++i) {
    if (ige <= maxg[i]) {
      break;
    }
  }
  ge16 = ige * 16.0;
  t = (ge16-cg[i]*ge16+lo[i]+lo0)/SOL_CSEC;
  *sol = t;
  tr = (t-*sol)*(SOL_CSEC/360000.0);
  *hour = tr;
  tr=(tr-*hour)*60;
  *min = tr;
  *csec = (tr-*min)*6000+0.5;
}

int llt2gcsc(int sol, int hour, int min, int csec) {
  int gcsc = (sol * SOL_CSEC + (hour*60+min)*6000+csec-2347019) * (1+1.0/72993);
  return gcsc % (1<<24);
}

int get_sequential_days_from_1976(int year, int doy) {
  int ret = -1;
  switch(year) {
    case 1976:
      ret = doy;
      break;
    case 1977:
      ret = 366 + doy;
      break;
    case 1978:
      ret = 366 + 365 + doy;
      break;
  }
  return ret;
}

int bcd2int(int bcd) {
  int ret = 0;
  int times = 1;
  while(bcd > 0) {
    ret += (bcd % 16) * times;
    bcd /= 16;
    times *= 10;
  }
  return ret;
}

command_status extract_command_status(int cmd_status) {
  command_status cs;
  cs.mode   = cmd_status & 0x03;
  cs.hatten = (cmd_status >>  2) & 0x07;
  cs.vatten = (cmd_status >>  5) & 0x07;
  cs.tlevel = (cmd_status >>  8) & 0x07;
  cs.fmode  = (cmd_status >> 11) & 0x01;
  cs.filt   = (cmd_status >> 12) & 0x02;
  cs.ztrig  = (cmd_status >> 14) & 0x01;
  cs.ytrig  = (cmd_status >> 15) & 0x01;
  cs.xtrig  = (cmd_status >> 16) & 0x01;
  cs.cal    = (cmd_status >> 17) & 0x03;
  return cs;
}

void print_command_status(const command_status* cs, int verbose) {
  const char* modes[4] = {"NORMAL","HIGH","EVENT","NORMAL"};
  const char* attens[8] = {"18DB"," 0DB","30DB","12DB",
			   "24DB"," 6DB","36DB","18DB"};
  
  const char* tlevels[8] = {"X12"," X8","X20","X12","X16","X12", " X4","X12"};
  const char* filts[4] = {"2.HZ",".5HZ","1.HZ","4.HZ"};
  const char* fmodes[2] = {"STEP","FIX"};
  const char* xtrigs[2] = {"XON","XOFF"};
  const char* ytrigs[2] = {"YON","YOFF"};
  const char* ztrigs[2] = {"ZON","ZOFF"};
  const char* cals[4] = {"CALON","CALON","CALOFF","CALON"};
  
  if (verbose) {
    printf("%-6s(%d) %-4s(%d) %-4s(%d) %-3s(%d) %-4s(%d) %-4s(%d) %-4s(%d) %-4s(%d) %-4s(%d) %-6s(%d)",
           modes[cs->mode],cs->mode,
           attens[cs->vatten],cs->vatten,
           attens[cs->hatten],cs->hatten,
           tlevels[cs->tlevel], cs->tlevel,
           filts[cs->filt], cs->filt,
           fmodes[cs->fmode],cs->fmode,
           xtrigs[cs->xtrig],cs->xtrig,
           ytrigs[cs->ytrig],cs->ytrig,
           ztrigs[cs->ztrig],cs->ztrig,
           cals[cs->cal], cs->cal);
  } else {
    printf("%-6s %-4s %-4s %-3s %-4s %-4s %-4s %-4s %-4s %-6s",
           modes[cs->mode],
           attens[cs->vatten],
           attens[cs->hatten],
           tlevels[cs->tlevel],
           filts[cs->filt],
           fmodes[cs->fmode],
           xtrigs[cs->xtrig],
           ytrigs[cs->ytrig],
           ztrigs[cs->ztrig],
           cals[cs->cal]);
  }
}
