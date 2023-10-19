from base64 import decode
import binascii

from utils import open_windows_partition


class NTFS:
    def __init__(self, drive_name: str) -> None:
        self.raw_data = None
        try:
            with open_windows_partition(drive_name) as drive:
                self.raw_data = drive.read(512)
        except FileNotFoundError:
            print("Drive not found")
            exit(1)

    def print_raw_bpb(self) -> None:
        str_data = binascii.hexlify(self.raw_data).decode("utf-8")

        # Print header
        print("offset ", end=" ")
        for i in range(0, 16):
            print("{:2x}".format(i), end=' ')
        print()

        # print 16 byte each line
        for i in range(0, len(str_data), 32):
            line = str_data[i:i+32]

            # print offset
            offset = int(i / 32)
            print("{:07x}0".format(offset), end=" ")

            # print hex
            for j in range(0, len(line), 2):
                print(line[j:j+2], end=' ')

            # print ascii
            for j in range(0, len(line), 2):
                char = line[j:j+2]
                # ignore \r \n

                if int(char, 16) >= 32 and int(char, 16) <= 126:
                    print(chr(int(char, 16)), end='')
                else:
                    print(".", end='')
            print()
