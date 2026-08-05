/**
 *  @file      vusinfo.c
 *  @brief     Show VUS information
 *  @author    Yukio Yamamoto
 *  @date      November 25, 2010
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <unistd.h>

#ifndef TRUE
#define TRUE 1
#endif

#ifndef FALSE
#define FALSE 0
#endif

#include "vus.h"
#include "vus_utils.h"
#include "vus_bit_stream.h"

#define MAX_EVENT_BITS 2700

#define SET_ARG(var,n,size) {strncpy(var, argv[n], size); var[size] = '\0';}

void usage(const char* cmd) {
  fprintf(stderr, "usage: %s [-68bfdenhzv] vkg-tape\n", cmd);
  fprintf(stderr, "\n");
  fprintf(stderr,
          "  options:\n"
          "    6 ... show 6-bit byte dump in octal\n"
          "    b ... show 6-bit byte dump in hex (for BCD)\n"
          "    8 ... show 8-bit byte dump in hex\n"
          "    f ... show frame info\n"
          "    d ... show data\n"
          "    e ... show EVENT data only\n"
          "    n ... show NORMAL data only\n"
          "    h ... show HIGH DATA RATE data only\n"
          "    z ... show nothing if cal mode is zero\n"
          "    v ... enable verbose mode\n");
}

int main(int argc, char** argv) {
  
  //Generic variables
  FILE* f;
  char filename[PATH_MAX+1];
  unsigned char buf[SIZE_BUFFER];
  
  int frame;
  int gcsc_index;
  int r;
  int rec_no;
  unsigned char bits[MAX_EVENT_BITS];
  int sol_start, sol_end = -1;
  int loop;
  
  // headers
  vus_header vh;
  seisf_header sh;
  frame_header fh;
  
  // data
  seismic_data data[MAX_CHANGES];
  
  // flags
  int flag_6bit_dump = 0;
  int flag_8bit_dump = 0;
  int flag_6bit_hex_dump = 0;
  int flag_frame_info = 0;
  int flag_data = 0;
  int flag_event_data = 0;
  int flag_normal_data = 0;
  int flag_high_data = 0;
  int flag_cal_zero = 0;
  int flag_verbose = 0;
  
  // getopt
  int ch;
  extern char *optarg;
  extern int optind, opterr;
  
  while ((ch = getopt(argc, argv, "68bfdenhzv")) != -1) {
    switch (ch) {
    case '6':
      flag_6bit_dump = 1;
      break;
    case '8':
      flag_8bit_dump = 1;
      break;
    case 'b':
      flag_6bit_hex_dump = 1;
      break;
    case 'f':
      flag_frame_info = 1;
      break;
    case 'd':
      flag_data = 1;
      break;
    case 'e':
      flag_event_data = 1;
      break;
    case 'n':
      flag_normal_data = 1;
      break;
    case 'h':
      flag_high_data = 1;
      break;
    case 'z':
      flag_cal_zero = 1;
    case 'v':
      flag_verbose = 1;
      break;
    }
  }
  argc -= optind;
  
  if (argc != 1) {
    usage(argv[0]);
    return EXIT_FAILURE;
  }
  argv += optind;
  
  // ----------------------------------------
  // PROGRAM MAIN
  // ----------------------------------------
  SET_ARG(filename,0,PATH_MAX);
  
  if ((f = fopen(filename, "rb")) == NULL) {
    fprintf(stderr, "no such file: %s\n", filename);
    return EXIT_FAILURE;
  }
  
  // ----------------------------------------
  // Read Exabyte header
  // ----------------------------------------
  rec_no = 0;
  while( (r = fread(buf, sizeof(unsigned char), SIZE_RECORD_HEADER, f)) > 0) {
    if (r != SIZE_RECORD_HEADER ) {
      fprintf(stderr, "file may be corrupted.\n");
      fclose(f);
      return EXIT_FAILURE;;
    }
    vh = get_exb_header(buf);
    
    if (strncmp(vh.label, "VUS", 3) != 0) {
      fprintf(stderr,
              "The Viking tape must be VUS tape (vkg.47-vkg.56).\n"
              "See University of Texas Institute for Geophysics Technical Report No.118.\n");
      fclose(f);
      return EXIT_FAILURE;
    }
    
    // ----------------------------------------
    // Read VUS tape data
    // ----------------------------------------
    while((r = fread(buf, sizeof(unsigned char), vh.length, f))>0) {
      if (r != vh.length && r <= 0) break;
      
      // Rewind if new USEIS header is found 
      if (check_vus_useis_header(buf)) {
        fseek(f,-vh.length,SEEK_CUR);
        break;
      }
      
      for(frame=0; frame<vh.length / BYTE_PER_FRAME; ++frame) {
        unsigned char* p = &buf[frame*BYTE_PER_FRAME];
	
	if (get_vus_frame_type(p,BYTE_PER_FRAME) == VUS_FRAME_TYPE_ALL_ONE) {
	  continue;
	}
	
	// word 3   24-35  GMT day-of-the-year of SEISF processing in 4-bit BCD
        sh.doy  = bcd2int(get_vus_data(p, 3, 24, 35));
        
	// word 5   12-19  Last 2 digits of year in 4-bit BCD
        sh.year = 1900 + bcd2int(get_vus_data(p, 5, 12, 19));
	
	make_bit_stream(p, bits);
	
	loop = extract_data_from_bit_stream(bits, data);
	for(gcsc_index=0; gcsc_index<loop; ++gcsc_index) {
	  
	  // convert GCSC count to LLT
	  gcsc2llt(data[gcsc_index].gcsc,
		   get_sequential_days_from_1976(sh.year,sh.doy),
		   &fh.sol, &fh.hour, &fh.min, &fh.csec);
	  
	  if (flag_frame_info) {
	    printf("%4d %3d %8d ", sh.year,sh.doy,data[gcsc_index].gcsc);
	    print_command_status(&data[gcsc_index].cs, flag_verbose);
	    printf(" %3d %2d/%02d:%02d:%02d.%02d\n",
		   fh.change_code,fh.sol,fh.hour,fh.min,(int)(fh.csec/100),fh.csec%100);
	  }
	  
	  if (data[gcsc_index].cs.cal == 0 && flag_cal_zero) {
	    rec_no++;
	    continue;
	  }
	  
	  // Update sol
	  if (rec_no == 0 && frame == 0) {
	    sol_start = fh.sol;
	  }
          
	  if ((sh.year >= 1976 && sh.year <= 1978) &&
	      fh.sol >= 0 && fh.change_code == 0 && data[gcsc_index].cs.cal != 0) {
	    sol_end = fh.sol;
	  }
          
	  if (flag_event_data && data[gcsc_index].cs.mode != MODE_EVENT) {
	    rec_no++;
	    continue;
	  }
          
	  if (flag_normal_data &&
              (data[gcsc_index].cs.mode != MODE_NORMAL || data[gcsc_index].cs.mode != MODE_NORMAL2)) {
	    rec_no++;
	    continue;
	  }
          
	  if (flag_high_data && data[gcsc_index].cs.mode != MODE_HIGH) {
	    rec_no++;
	    continue;
	  }
	  
	  if (flag_6bit_dump) {
	    vus_6bit_dump(p, BYTE_PER_FRAME);
	  }
	  
	  if (flag_6bit_hex_dump) {
	    vus_6bit_hex_dump(p, BYTE_PER_FRAME);
	  }
	  
	  if (flag_8bit_dump) {
	    vus_8bit_dump(p, BYTE_PER_FRAME);
	  }
	  
	  if (flag_data) {
	    int i;
	    for(i=0; i<data[gcsc_index].ndata; ++i) {
	      if (data[gcsc_index].cs.mode == MODE_EVENT) {
		printf("%4d %4d %4d %4d %4d %4d %4d\n", i,
		       data[gcsc_index].amp[0][i], data[gcsc_index].axis[0][i],
                       data[gcsc_index].amp[1][i], data[gcsc_index].axis[1][i],
                       data[gcsc_index].amp[2][i], data[gcsc_index].axis[2][i]);
		        
	      } else {
		printf("%4d %4d %4d %4d\n", i,
		       data[gcsc_index].amp[0][i], data[gcsc_index].amp[1][i], data[gcsc_index].amp[2][i]);
	      }
	    }
	  }
	}
      }
      rec_no++;
    }
  }
  
  printf("%d %s %d %d %d  USEIS  %03d-%03d\n", vh.id, vh.label, vh.file_no, rec_no, vh.length, sol_start, sol_end);
  
  fclose(f); 
  return EXIT_SUCCESS;
}
