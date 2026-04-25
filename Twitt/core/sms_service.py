import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSIR:
    def __init__(self):
        self.api_key = settings.SMS_IR_API_KEY
        self.line_number = settings.SMS_IR_LINE_NUMBER
        self.template_id = settings.SMS_IR_TEMPLATE_ID
        self.base_url = "https://ws.sms.ir/"

    def send_verification_code(self, phone_number, code):
        url = f"{self.base_url}api/MessageSend"

        logger.info(f"========== شروع ارسال SMS ==========")
        logger.info(f"شماره: {phone_number}")
        logger.info(f"کد: {code}")
        token = "LCd2ar6gzF9MC4k4oxtyEVjDvmfC6qgQ1ReOiVcgPau76SEi"

        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-sms-ir-secure-token": token,
            }

            data = {
                "LineNumber": self.line_number,
                "Mobile": phone_number,
                "TemplateId": self.template_id,
                "Parameters": [
                    {"Name": "OTP", "Value": str(code)},
                ]
            }

            logger.info(f"Request: {data}")

            response = requests.post(url, json=data, headers=headers, timeout=15)
            result = response.json()

            logger.info(f"Response: {result}")

            return result

        except Exception as e:
            logger.error(f"خطا: {e}")
            raise


def send_sms(phone_number, code):
    sms_service = SMSIR()
    return sms_service.send_verification_code(phone_number, code)
