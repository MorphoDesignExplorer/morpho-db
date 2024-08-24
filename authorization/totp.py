import base64
import binascii
import hmac
from hashlib import sha1, sha256, sha512
import unittest
from time import time


class TOTP:
    """
    A TOTP Implementation based on RFC 6238.

    Note to self:
        SHA1 is the standard hash algorithm used to generate TOTPs on authenticator applications, with 6 digits.
        Also, the standard time window used is 30 seconds.
    """
    def __init__(self, key: str,  step: int = None, return_digits: int = None, algorithm = None):
        """
        Creates an object that generates OTPs based on a Base32 secret.

        :param key: Base32 encoded secret.
        :param step: Time window in which OTP is valid. If left blank, the OTP stays valid for 30 seconds once generated.
        :param return_digits: Number of digits the OTP must contain. If left blank, the OTP has 8 digits.
        :param algorithm: The algorithm used to generate the OTP hash. If left blank, uses SHA1.
        :returns: A TOTP object.
        """

        try:
            key = base64.b32decode(key)

            if not isinstance(key, bytes):
                raise TypeError("key must be of type 'bytes'")
            
            if return_digits < 1:
                raise ValueError("return_digits must be greater than 1")
            
            if step < 1:
                raise ValueError("step must be greater than 1")

            self.key_bytes = key
            self.algorithm = sha1 if algorithm is None else algorithm
            self.step = 30 if step is None else step
            self.return_digits = 8 if return_digits is None else return_digits

        except binascii.Error:
            raise ValueError(f"Please provide a valid Base32 secret.")

        except Exception as e:
            raise Exception(f"Arbitrary Error: {e}")

    def otp_at(self, t: int):
        """
        Get the OTP at time `t`.

        :param t: number of seconds since the UNIX epoch
        :returns: An OTP with `return_digits` number of digits.
        """
        if not isinstance(t, int):
            raise TypeError("t must be of type 'int'")
        t_init = 0
        normalized_time = (t - t_init) // self.step
        return self.generateTOTP(normalized_time)

    def otp_now(self):
        """
        Get the OTP at the current time.

        :returns: An OTP with `return_digits` number of digits.
        """
        t_init = 0
        normalized_time = int((time() - t_init) // self.step)
        return self.generateTOTP(normalized_time)

    def generateTOTP(self, time: int):
        """
        Generates an OTP based on the time interval block provided.

        :param time: Time interval block
        :returns: An OTP with `return_digits` number of digits.
        """
        result = ''

        # convert time to bytes; must be 8 bytes long
        time_bytes = time.to_bytes(8, "big")
        key_bytes = self.key_bytes

        # hash
        hash_value = hmac.new(key_bytes, time_bytes, self.algorithm).digest()

        # get offset
        offset = hash_value[len(hash_value) - 1] & 0xf

        # calculate binary against offset
        binary = ((hash_value[offset] & 0x7f) << 24) | ((hash_value[offset+1] & 0xff) << 16) | ((hash_value[offset+2] & 0xff) << 8)  | ((hash_value[offset+3] & 0xff))

        otp = binary % (10 ** self.return_digits)

        result = str(otp)
        result = result.zfill(self.return_digits)

        return result


class TestTOTP(unittest.TestCase):
    table = [
        [59, "94287082", sha1],
        [59, "46119246", sha256],
        [59, "90693936", sha512],
        [1111111109, "07081804", sha1],
        [1111111109, "68084774", sha256],
        [1111111109, "25091201", sha512],
        [1111111111, "14050471", sha1],
        [1111111111, "67062674", sha256],
        [1111111111, "99943326", sha512],
        [1234567890, "89005924", sha1],
        [1234567890, "91819424", sha256],
        [1234567890, "93441116", sha512],
        [2000000000, "69279037", sha1],
        [2000000000, "90698825", sha256],
        [2000000000, "38618901", sha512],
        [20000000000, "65353130", sha1],
        [20000000000, "77737706", sha256],
        [20000000000, "47863826", sha512],
    ]

    def test_totp_sha1(self):
        key = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        for t, otp, algorithm in self.table:
            if algorithm == sha1:
                TOTP_obj = TOTP(key, 30, 8, sha1)
                generated_otp = TOTP_obj.otp_at(t)
                self.assertEqual(generated_otp, otp)

    def test_totp_sha256(self):
        key = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZA===="
        for t, otp, algorithm in self.table:
            if algorithm == sha256:
                TOTP_obj = TOTP(key, 30, 8, sha256)
                generated_otp = TOTP_obj.otp_at(t)
                self.assertEqual(generated_otp, otp)

    def test_totp_sha512(self):
        key = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNA="
        for t, otp, algorithm in self.table:
            if algorithm == sha512:
                TOTP_obj = TOTP(key, 30, 8, sha512)
                generated_otp = TOTP_obj.otp_at(t)
                self.assertEqual(generated_otp, otp)


if __name__ == "__main__":
    # key = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"          # Get Base32 encoded secret
    # TOTP_obj = TOTP(key, 30, 6, sha1)                 # Generate object with SHA1 hashing
    # print(TOTP_obj.otp_now())                         # Get current OTP
    unittest.main()

