/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32u5xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_LPTIM_MspPostInit(LPTIM_HandleTypeDef *hlptim);

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define PH_leaf3_Pin GPIO_PIN_13
#define PH_leaf3_GPIO_Port GPIOC
#define IPROPI_leaf3_Pin GPIO_PIN_0
#define IPROPI_leaf3_GPIO_Port GPIOC
#define nFAULT_leaf3_Pin GPIO_PIN_1
#define nFAULT_leaf3_GPIO_Port GPIOC
#define IPROPI_leaf4_Pin GPIO_PIN_2
#define IPROPI_leaf4_GPIO_Port GPIOC
#define nFAULT_leaf4_Pin GPIO_PIN_3
#define nFAULT_leaf4_GPIO_Port GPIOC
#define ENC_leaf4_Pin GPIO_PIN_0
#define ENC_leaf4_GPIO_Port GPIOA
#define ENC_leaf3_Pin GPIO_PIN_1
#define ENC_leaf3_GPIO_Port GPIOA
#define RC_OUT_leaf4_Pin GPIO_PIN_2
#define RC_OUT_leaf4_GPIO_Port GPIOA
#define ENC_leaf2_Pin GPIO_PIN_3
#define ENC_leaf2_GPIO_Port GPIOA
#define IPROPI_leaf1_Pin GPIO_PIN_4
#define IPROPI_leaf1_GPIO_Port GPIOA
#define IPROPI_leaf2_Pin GPIO_PIN_5
#define IPROPI_leaf2_GPIO_Port GPIOA
#define EN_leaf3_Pin GPIO_PIN_6
#define EN_leaf3_GPIO_Port GPIOA
#define EN_leaf4_Pin GPIO_PIN_7
#define EN_leaf4_GPIO_Port GPIOA
#define IPROPI_yaw_Pin GPIO_PIN_4
#define IPROPI_yaw_GPIO_Port GPIOC
#define PH_leaf1_Pin GPIO_PIN_5
#define PH_leaf1_GPIO_Port GPIOC
#define EN_leaf1_Pin GPIO_PIN_0
#define EN_leaf1_GPIO_Port GPIOB
#define EN_leaf2_Pin GPIO_PIN_1
#define EN_leaf2_GPIO_Port GPIOB
#define nFAULT_leaf1_Pin GPIO_PIN_2
#define nFAULT_leaf1_GPIO_Port GPIOB
#define ENC_leaf1_Pin GPIO_PIN_10
#define ENC_leaf1_GPIO_Port GPIOB
#define PH_leaf2_Pin GPIO_PIN_12
#define PH_leaf2_GPIO_Port GPIOB
#define nFAULT_leaf2_Pin GPIO_PIN_13
#define nFAULT_leaf2_GPIO_Port GPIOB
#define RC_OUT_leaf1_Pin GPIO_PIN_14
#define RC_OUT_leaf1_GPIO_Port GPIOB
#define RC_OUT_leaf2_Pin GPIO_PIN_15
#define RC_OUT_leaf2_GPIO_Port GPIOB
#define DRV_nSLEEP_Pin GPIO_PIN_6
#define DRV_nSLEEP_GPIO_Port GPIOC
#define LED_HB_Pin GPIO_PIN_7
#define LED_HB_GPIO_Port GPIOC
#define nFAULT_yaw_Pin GPIO_PIN_8
#define nFAULT_yaw_GPIO_Port GPIOC
#define PH_yaw_Pin GPIO_PIN_9
#define PH_yaw_GPIO_Port GPIOC
#define RC_OUT_yaw_Pin GPIO_PIN_8
#define RC_OUT_yaw_GPIO_Port GPIOA
#define EN_yaw_Pin GPIO_PIN_9
#define EN_yaw_GPIO_Port GPIOA
#define CAN1_RX_Pin GPIO_PIN_11
#define CAN1_RX_GPIO_Port GPIOA
#define CAN1_TX_Pin GPIO_PIN_12
#define CAN1_TX_GPIO_Port GPIOA
#define YAW_ENC_A_Pin GPIO_PIN_15
#define YAW_ENC_A_GPIO_Port GPIOA
#define YAW_ENC_A_EXTI_IRQn EXTI15_IRQn
#define DBG_TX_Pin GPIO_PIN_10
#define DBG_TX_GPIO_Port GPIOC
#define DBG_RX_Pin GPIO_PIN_11
#define DBG_RX_GPIO_Port GPIOC
#define YAW_LIM_Pin GPIO_PIN_12
#define YAW_LIM_GPIO_Port GPIOC
#define YAW_LIM_EXTI_IRQn EXTI12_IRQn
#define PH_leaf4_Pin GPIO_PIN_2
#define PH_leaf4_GPIO_Port GPIOD
#define YAW_ENC_B_Pin GPIO_PIN_3
#define YAW_ENC_B_GPIO_Port GPIOB
#define YAW_ENC_B_EXTI_IRQn EXTI3_IRQn
#define BUCK_SYNC_Pin GPIO_PIN_4
#define BUCK_SYNC_GPIO_Port GPIOB
#define LED_DATA_Pin GPIO_PIN_5
#define LED_DATA_GPIO_Port GPIOB
#define RC_OUT_leaf3_Pin GPIO_PIN_6
#define RC_OUT_leaf3_GPIO_Port GPIOB
#define YAW_HOME_Pin GPIO_PIN_7
#define YAW_HOME_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
