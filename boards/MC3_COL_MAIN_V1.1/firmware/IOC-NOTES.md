# .ioc grammar notes — MC3_COL_MAIN_U595 (CubeMX 6.18.1, STM32U595RJT6)

Reference for hand-editing `MC3_COL_MAIN_U595.ioc`. Everything below was verified by
diffing the file before/after GUI saves during the 2026-08-27 setup session. Design
rationale lives in the vault (Main-Board-01 rung, MCU Pinout); this is syntax only.

## Pin blocks

```
PB5.Signal=GPIO_Output            # or S_TIM3_CH1, GPXTI12, USART3_TX, ADC1_IN9, ...
PB5.Locked=true                   # REQUIRED on every hand-authored pin — without it the
                                  # load-time auto-placer may move the signal elsewhere
PB5.GPIOParameters=GPIO_Speed,GPIO_Label   # enumeration of which GPIO_* keys below exist;
                                           # a GPIO_* key NOT listed here is silently dropped
PB5.GPIO_Label=LED_DATA
PB5.GPIO_Speed=GPIO_SPEED_FREQ_HIGH
```

- Pins with alternate names are escaped verbatim as the key:
  `PB4\ (NJTRST).Signal=...`, `PA15\ (JTDI).Signal=...`, `PB3\ (JTDO/TRACESWO).Signal=...`
- Every pin also needs a `Mcu.PinN=<pin>` list entry and `Mcu.PinsNb` bumped.

## Shared-signal (SH) bindings — timer/LPTIM channels

A pin whose Signal is `S_TIMx_CHn` needs a matching SH line naming the channel mode,
and the peripheral needs the channel in its IPParameters:

```
PA3.Signal=S_TIM5_CH4
SH.S_TIM5_CH4.0=TIM5_CH4,Input_Capture4_from_TI4
TIM5.Channel-Input_Capture4_from_TI4=TIM_CHANNEL_4
SH.S_LPTIM1_CH2.0=LPTIM1_CH2,OutputIO_CH2
```

## EXTI pins

```
PC12.Signal=GPXTI12
SH.GPXTI12.0=GPIO_EXTI12
PC12.GPIOParameters=GPIO_Label,GPIO_ModeDefaultEXTI
PC12.GPIO_ModeDefaultEXTI=GPIO_MODE_IT_RISING        # _RISING_FALLING for both edges
NVIC.EXTI12_IRQn=true\:0\:0\:false\:false\:true\:true\:true\:true
#                 en  pre sub |     |     ... (colon-separated, colons escaped \:)
```

## Virtual pins (no package pin) — clock-mode / channel-active / ICACHE

```
VP_LPTIM1_VS_LPTIM_counterModeInternalClock.Mode=Counts__internal_clock_event_00
VP_LPTIM1_VS_LPTIM_counterModeInternalClock.Signal=LPTIM1_VS_LPTIM_counterModeInternalClock
VP_LPTIM1_VS_CH2.Mode=Channel_2_Active
VP_ICACHE_VS_ICACHE.Mode=DefaultMode
VP_ICACHE_VS_ICACHE.Signal=ICACHE_VS_ICACHE
```

Each VP also gets a `Mcu.PinN=` entry, and the peripheral a `Mcu.IPn=` entry
(`Mcu.IP6=ICACHE`) with `Mcu.IPNb` bumped.

## Peripheral parameter blocks

Every `<IP>.<Param>=` key must also be listed in `<IP>.IPParameters=` (comma list) —
same silent-drop rule as GPIOParameters.

### Timers (as configured)

```
TIM3.Period=7999                                  # 160 MHz / 8000 = 20 kHz; PSC omitted = 0
TIM3.TIM_MasterOutputTrigger=TIM_TRGO_UPDATE      # TRGO on Update -> ADC trigger
TIM1.Period=7999
LPTIM1.Period=15                                  # HSI16/16 -> 1.000 MHz BUCK_SYNC
LPTIM1.OCPulse_2=8                                # ~50% on channel 2
RCC.LPTIM1CLockSelectionVirtual=RCC_LPTIM1CLKSOURCE_HSI   # (sic: "CLock") kernel mux —
                                                  # LPTIM kernel clock is MSIK/LSI/HSI16/LSE only
```

Note: TIM2/3/4/5 on U5 are 32-bit — a "Reset Configuration" puts Period back to
4294967295, not 65535.

### ADC1 (5-rank scan, hardware-triggered, DMA circular)

```
ADC1.NbrOfConversion=5
ADC1.ScanConvMode=ADC_SCAN_ENABLE
ADC1.ExternalTrigConv=ADC_EXTERNALTRIG_T3_TRGO
ADC1.ExternalTrigConvEdge=ADC_EXTERNALTRIGCONVEDGE_RISING
ADC1.DMAContinuousRequests=ENABLE
ADC1.Overrun=ADC_OVR_DATA_OVERWRITTEN
# per rank N (0-based), each key suffixed \#ChannelRegularConversion:
ADC1.Channel-0\#ChannelRegularConversion=ADC_CHANNEL_9      # IPROPI_leaf1 ... rank order
ADC1.Rank-0\#ChannelRegularConversion=1                     #   9,10,1,3,13
ADC1.SamplingTime-0\#ChannelRegularConversion=ADC_SAMPLETIME_68CYCLES
ADC1.OffsetNumber-0\#ChannelRegularConversion=ADC_OFFSET_NONE
```

### GPDMA1 channel 0 (ADC1, circular, half-word)

Per-channel params are suffixed `_GPDMACH<n>`, all enumerated in `GPDMA1.IPParameters`:

```
GPDMA1.REQUEST_GPDMACH0=GPDMA1_REQUEST_ADC1
GPDMA1.CIRCULARMODE_GPDMACH0=ENABLE
GPDMA1.PRIORITY_LL_CIRCULAR_GPDMACH0=DMA_LOW_PRIORITY_HIGH_WEIGHT   # GUI "High"
GPDMA1.SRCDATAWIDTH_GPDMACH0=DMA_SRC_DATAWIDTH_HALFWORD             # src no-increment is default
GPDMA1.DESTDATAWIDTH_GPDMACH0=DMA_DEST_DATAWIDTH_HALFWORD
GPDMA1.DESTINC_GPDMACH0=DMA_DINC_INCREMENTED
GPDMA1.IPHANDLE_GPDMACH0-SIMPLEREQUEST_GPDMACH0=__NULL              # standard request mode
```

## Hard-won rules

1. **`Locked=true` on every pin** or a reload can silently re-place signals
   (observed: EXTI15→PC15, I2C1_SDA→PB3, USART3→PA7/PC5).
2. **Enumeration keys are gatekeepers**: `GPIOParameters` and `IPParameters` must list
   every key you add, or CubeMX drops the setting on next load without erroring.
3. LPTIM1 kernel clock cannot come from the PLL — HSI16 is the only precise fast source,
   so BUCK_SYNC is frequency-pinned (1.000 MHz), not phase-locked to the system clock.
4. After any hand edit, open in CubeMX, save, and diff — the round-trip is the only
   proof the grammar was accepted.
