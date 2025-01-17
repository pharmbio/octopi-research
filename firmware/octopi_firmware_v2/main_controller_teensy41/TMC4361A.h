/*
   TMC4361A.h
   This file includes other header files with useful constants and type declarations. It also defines constants, macros, and types, and prototypes the functions in TMC4316A.cpp

    Created on: 18.07.2017
        Author: LK, with additions from Kevin Marx, 7/14/2022
*/

#ifndef TMC_IC_TMC4361A_H_
#define TMC_IC_TMC4361A_H_

#include "tmc/helpers/API_Header.h"
#include "TMC4361A_Register.h"
#include "TMC4361A_Constants.h"
#include "TMC4361A_Fields.h"

// Constants for indexing ramp parameter array
#define N_RPARAM   9
#define BOW1_IDX   0
#define BOW2_IDX   1
#define BOW3_IDX   2
#define BOW4_IDX   3
#define AMAX_IDX   4
#define DMAX_IDX   5
#define ASTART_IDX 6
#define DFINAL_IDX 7
#define VMAX_IDX   8
// Constants for indexing current scale value array
#define N_CPARAM      5
#define CSCALE_IDX    0
#define HOLDSCALE_IDX 1
#define DRV2SCALE_IDX 2
#define DRV1SCALE_IDX 3
#define BSTSCALE_IDX  4

// Helper macros
#define TMC4361A_FIELD_READ(tdef, address, mask, shift) \
  FIELD_GET(tmc4361A_readInt(tdef, address), mask, shift)
#define TMC4361A_FIELD_WRITE(tdef, address, mask, shift, value) \
  (tmc4361A_writeInt(tdef, address, FIELD_SET(tmc4361A_readInt(tdef, address), mask, shift, value)))


// Typedefs
typedef struct
{
  ConfigurationTypeDef *config;
  int velocity;
  int oldX;
  uint32_t oldTick;
  int32_t registerResetState[TMC4361A_REGISTER_COUNT];
  uint8_t registerAccess[TMC4361A_REGISTER_COUNT];
  int32_t xmin;
  int32_t xmax;
  int32_t xhome;
  int32_t rampParam[N_RPARAM];
  int32_t cscaleParam[N_CPARAM];
  float   threadPitch;
  uint16_t stepsPerRev;
  uint16_t microsteps;
  bool velocity_mode;
  
  //TMotorConfig motorConfig;
  //TClosedLoopConfig closedLoopConfig;
  uint8_t status;
  ConfigurationTypeDef *cover;
} TMC4361ATypeDef;

typedef void (*tmc4361A_callback)(TMC4361ATypeDef*, ConfigState);

// Default Register Values
#define R10 0x00040001  // STP_LENGTH_ADD
#define R20 0x00000001  // RAMPMODE

static const int32_t tmc4361A_defaultRegisterResetState[TMC4361A_REGISTER_COUNT] =
{
  //	0,   1,   2,   3,   4,   5,   6,   7,   8,   9,   A,   B,   C,   D,   E,   F
  N_A, 0,   0,   0,   0,   0,   N_A, N_A, 0,   0,   N_A, N_A, 0,   0,   0,   0,   // 0x00 - 0x0F
  R10, 0,   N_A, 0,   0,   0,   0,   0,   0,   0,   0,   0,   N_A, 0,   0,   N_A, // 0x10 - 0x1F
  R20, 0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   // 0x20 - 0x2F
  0,   N_A, 0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   // 0x30 - 0x3F
  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   // 0x40 - 0x4F
  0,   0,   0,   N_A, 0,   0,   N_A, N_A, N_A, 0,   0,   0,   0,   0,   0,   0,   // 0x50 - 0x5F
  0,   0,   N_A, 0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   // 0x60 - 0x6F
  N_A, N_A, N_A, N_A, N_A, N_A, N_A, N_A, N_A, 0,   0,   N_A, N_A, 0,   N_A, 0    // 0x70 - 0x7F
};

#undef R10
#undef R20

// Register access permissions:
//     0x00: none (reserved)
//     0x01: read
//     0x02: write
//     0x03: read/write
//     0x13: read/write, separate functions/values for reading or writing
//     0x23: read/write, holds read or write to clear flags
//     0x42: write, has hardware presets on reset
//     0x43: read/write, has hardware presets on reset
//     0x53: read/write, has hardware presets on reset, separate functions/values for reading or writing
static const uint8_t tmc4361A_defaultRegisterAccess[TMC4361A_REGISTER_COUNT] =
{
  //  0     1     2     3     4     5     6     7     8     9     A     B     C     D     E     F
  0x43, 0x03, 0x03, 0x03, 0x03, 0x03, 0x43, 0x43, 0x03, 0x03, 0x43, 0x43, 0x03, 0x03, 0x23, 0x01, // 0x00 - 0x0F
  0x03, 0x03, 0x43, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x43, 0x03, 0x03, 0x43, // 0x10 - 0x1F
  0x03, 0x03, 0x01, 0x01, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, // 0x20 - 0x2F
  0x03, 0x43, 0x03, 0x03, 0x03, 0x03, 0x13, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, // 0x30 - 0x3F
  0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, // 0x40 - 0x4F
  0x03, 0x13, 0x13, 0x42, 0x13, 0x02, 0x42, 0x42, 0x42, 0x03, 0x13, 0x13, 0x02, 0x13, 0x02, 0x02, // 0x50 - 0x5F
  0x02, 0x02, 0x42, 0x02, ____, 0x01, 0x01, 0x02, 0x02, 0x02, 0x01, 0x01, 0x13, 0x13, 0x01, 0x01, // 0x60 - 0x6F
  0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x13, 0x01, 0x13, 0x13, 0x02, 0x42, 0x01  // 0x70 - 0x7F
};

// Register constants (only required for 0x42 registers, since we do not have
// any way to find out the content but want to hold the actual value in the
// shadow register so an application (i.e. the TMCL IDE) can still display
// the values. This only works when the register content is constant.
static const TMCRegisterConstant tmc4361A_RegisterConstants[] =
{ // Use ascending addresses!
  { 0x53, 0xFFFFFFFF }, // ENC_POS_DEV_TOL
  { 0x56, 0x00A000A0 }, // SER_CLK_IN_HIGH, SER_CLK_IN_LOW
  { 0x57, 0x00F00000 }, // SSI_IN_CLK_DELAY, SSI_IN_WTIME
  { 0x58, 0x00000190 }, // SER_PTIME
  { 0x62, 0x00FFFFFF }, // ENC_VEL_ZERO
  { 0x70, 0xAAAAB554 }, // MSLUT[0]
  { 0x71, 0x4A9554AA }, // MSLUT[1]
  { 0x72, 0x24492929 }, // MSLUT[2]
  { 0x73, 0x10104222 }, // MSLUT[3]
  { 0x74, 0xFBFFFFFF }, // MSLUT[4]
  { 0x75, 0xB5BB777D }, // MSLUT[5]
  { 0x76, 0x49295556 }, // MSLUT[6]
  { 0x77, 0x00404222 }, // MSLUT[7]
  { 0x78, 0xFFFF8056 }, // MSLUTSEL
  { 0x7E, 0x00F70000 }, // START_SIN, START_SIN_90_120, DAC_OFFSET
};

// API Functions
// All functions act on one IC given by the TMC4361ATypeDef struct
extern void tmc4361A_readWriteArray(uint8_t channel, uint8_t *data, size_t length);

// SPI Communication
void tmc4361A_writeDatagram(TMC4361ATypeDef *tmc4361A, uint8_t address, uint8_t x1, uint8_t x2, uint8_t x3, uint8_t x4);
void tmc4361A_writeInt(TMC4361ATypeDef *tmc4361A, uint8_t address, int32_t value);
int32_t tmc4361A_readInt(TMC4361ATypeDef *tmc4361A, uint8_t address);
void tmc4361A_readWriteCover(TMC4361ATypeDef *tmc4361A, uint8_t *data, size_t length);

// Configuration
void tmc4361A_init(TMC4361ATypeDef *tmc4361A, uint8_t channel, ConfigurationTypeDef *config, const int32_t *registerResetState);
void tmc4361A_fillShadowRegisters(TMC4361ATypeDef *tmc4361A);
uint8_t tmc4361A_reset(TMC4361ATypeDef *tmc4361A);
uint8_t tmc4361A_restore(TMC4361ATypeDef *tmc4361A);
void tmc4361A_setRegisterResetState(TMC4361ATypeDef *tmc4361A, const int32_t *resetState);
void tmc4361A_setCallback(TMC4361ATypeDef *tmc4361A, tmc4361A_callback callback);
void tmc4361A_periodicJob(TMC4361ATypeDef *tmc4361A, uint32_t tick);

// Motion
void tmc4361A_rotate(TMC4361ATypeDef *tmc4361A, int32_t velocity);
void tmc4361A_right(TMC4361ATypeDef *tmc4361A, int32_t velocity);
void tmc4361A_left(TMC4361ATypeDef *tmc4361A, int32_t velocity);
void tmc4361A_stop(TMC4361ATypeDef *tmc4361A);
void tmc4361A_moveTo(TMC4361ATypeDef *tmc4361A, int32_t position, uint32_t velocityMax);
void tmc4361A_moveBy(TMC4361ATypeDef *tmc4361A, int32_t *ticks, uint32_t velocityMax);

// Helper functions
int32_t tmc4361A_discardVelocityDecimals(int32_t value);
uint8_t tmc4361A_calibrateClosedLoop(TMC4361ATypeDef *tmc4361A, uint8_t worker0master1);

#endif /* TMC_IC_TMC4361A_H_ */
