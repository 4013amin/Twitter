import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSIR:
    def __init__(self):
        self.api_key = settings.SMS_IR_API_KEY
        self.line_number = settings.SMS_IR_LINE_NUMBER
        self.base_url = "https://ws.sms.ir/"

    def send_verification_code(self, phone_number, code):
        url = f"{self.base_url}api/MessageSend"
        template_id = settings.SMS_IR_TEMPLATE_ID

        logger.info(f"========== شروع ارسال SMS ==========")
        logger.info(f"شماره: {phone_number}")
        logger.info(f"کد: {code}")
        logger.info(f"Template ID: {template_id}")
        logger.info(f"API Key: {self.api_key}")

        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-sms-ir-secure-token": self.api_key,
            }

            data = {
                "LineNumber": self.line_number,
                "Mobile": phone_number,
                "TemplateId": template_id,
                "Parameters": [
                    {
                        "Name": "OTP",
                        "Value": str(code)
                    },
                ]
            }

            logger.info(f"Request: {data}")

            response = requests.post(url, json=data, headers=headers, timeout=15)
            response_text = response.text
            status_code = response.status_code

            logger.info(f"Status Code: {status_code}")
            logger.info(f"Response: {response_text}")

            response.raise_for_status()
            result = response.json()
            logger.info(f"نتیجه: {result}")
            logger.info(f"========== پایان ارسال SMS ==========")

            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            logger.error(f"Response: {response_text}")
            raise
        except Exception as e:
            logger.error(f"خطا: {e}")
            raise


def send_sms(phone_number, code):
    sms_service = SMSIR()
    return sms_service.send_verification_code(phone_number, code)