from utils import open_windows_partition

import sys
import binascii
import time

# Constants
BPS_SIZE = 512
MFT_END = int.from_bytes(b'\xff\xff\xff\xff', byteorder=sys.byteorder)
MFT_ENTRY_SIZE = 1024
ATTR_FILE_NAME = 48
VOLUME_HEADER_OFFSET = 512

MFT_ENTRY_FLAGS = {
    "MFT_RECORD_IN_USE": 1,
    "MFT_RECORD_IS_DIRECTORY": 2,
    "MFT_RECORD_IN_EXTENDED": 4,
    "MFT_RECORD_IS_VIEW_INDEX": 8
}

FILE_ATTRIBUTE_FLAGS = {
    "READ_ONLY": 0x00000001,
    "HIDDEN": 0x00000002,
    "SYSTEM": 0x00000004,
    "ARCHIVE": 0x00000020,
    "DEVICE": 0x00000040,
    "NORMAL": 0x00000080,
    "TEMPORARY": 0x00000100,
    "SPARSE_FILE": 0x00000200,
    "REPARSE_POINT": 0x00000400,
    "COMPRESSED": 0x00000800,
    "OFFLINE": 0x00001000,
    "NOT_CONTENT_INDEXED": 0x00002000,
    "ENCRYPTED": 0x00004000,
    "DIRECTORY": 0x10000000,
    "INDEX_VIEW": 0x20000000
}

MFT_ATTRIBUTE_TYPE = {
    "$STANDARD_INFORMATION": 0x10,
    "$ATTRIBUTE_LIST": 0x20,
    "$FILE_NAME": 0x30,
    "$OBJECT_ID": 0x40,
    "$SECURITY_DESCRIPTOR": 0x50,
    "$VOLUME_NAME": 0x60,
    "$VOLUME_INFORMATION": 0x70,
    "$DATA": 0x80,
    "$INDEX_ROOT": 0x90,
    "$INDEX_ALLOCATION": 0xA0,
    "$BITMAP": 0xB0,
    "$REPARSE_POINT": 0xC0,
    "$EA_INFORMATION": 0xD0,
    "$EA": 0xE0,
    "$PROPERTY_SET": 0xF0,
    "$LOGGED_UTILITY_STREAM": 0x100
}


class NTFS:
    def __init__(self, drive_name: str) -> None:
        self.raw_data = None
        self.drive = open_windows_partition(drive_name)
        self.boot_sector = None
        self.current_offset = 0
        self.current_mft_index_entry = 0
        self.mft_attribute_header = None
        self.mft_entry_raw_data = None
        self.mft_entry_data = None
        try:
            self.raw_data = self.drive.read(512)
            self.__extract_bpb__()
        except FileNotFoundError:
            print("Drive not found")
            exit(1)

    def __extract_bpb__(self) -> dict:
        self.boot_sector = {
            "System ID": self.raw_data[0x03:0x0B].decode("utf-8"),
            "Bytes Per Sector": int.from_bytes(self.raw_data[0x0B:0x0D], byteorder=sys.byteorder),
            "Sectors Per Cluster": int.from_bytes(self.raw_data[0x0D:0x0E], byteorder=sys.byteorder),
            "Sectors Per track": int.from_bytes(self.raw_data[0x18:0x1A], byteorder=sys.byteorder),
            "Number Of Heads": int.from_bytes(self.raw_data[0x1A:0x1C], byteorder=sys.byteorder),
            "Total Sector": int.from_bytes(self.raw_data[0x28:0x30], byteorder=sys.byteorder),
            "MFT Cluster": int.from_bytes(self.raw_data[0x30:0x38], byteorder=sys.byteorder),
            "MFT Mirror Cluster": int.from_bytes(self.raw_data[0x38:0x40], byteorder=sys.byteorder),
            "Size of MTF Entry": int.from_bytes(self.raw_data[0x40:0x44], byteorder=sys.byteorder),
        }
        return self.boot_sector

    def __extract_mft__(self) -> dict:

        self.current_offset = self.boot_sector["MFT Cluster"] * self.boot_sector["Sectors Per Cluster"] * \
            self.boot_sector["Bytes Per Sector"] + \
            self.current_mft_index_entry * MFT_ENTRY_SIZE
        self.drive.seek(self.current_offset)

        # READ FIRST MFT ENTRY
        self.mft_entry_raw_data = self.drive.read(MFT_ENTRY_SIZE)

        # debug
        self.print_raw_mft(self.mft_entry_raw_data)
        # end debug

        self.mft_entry_header = {
            "Signature": self.mft_entry_raw_data[0x0:0x4].decode("utf-8"),
            "Sequence Number": int.from_bytes(self.mft_entry_raw_data[0x4:0x6], byteorder=sys.byteorder),
            "Reference Count": int.from_bytes(self.mft_entry_raw_data[0x6:0x8], byteorder=sys.byteorder),
            "Offset to the first attribute": int.from_bytes(self.mft_entry_raw_data[0x14:0x16], byteorder=sys.byteorder),
            "Entry Flags": self.__get_entry_flags__(int.from_bytes(self.mft_entry_raw_data[0x16:0x18], byteorder=sys.byteorder)),
            "Real size of the file": int.from_bytes(self.mft_entry_raw_data[0x18:0x1C], byteorder=sys.byteorder),
            "Total entry size": int.from_bytes(self.mft_entry_raw_data[0x1C:0x20], byteorder=sys.byteorder),
            "Base reference": int.from_bytes(self.mft_entry_raw_data[0x20:0x28], byteorder=sys.byteorder),
        }

        if self.mft_entry_header["Signature"] != "FILE":
            self.current_mft_index_entry += 1
            return

        # debug
        print("[MFT ENTRY]", self.mft_entry_header)

        # ATTRIBUTE THỨ NHẤT - STANDARD INFORMATION
        self.current_offset += self.mft_entry_header["Offset to the first attribute"]
        self.drive.seek(self.current_offset)
        self.mft_entry_raw_data = self.drive.read(16)
        self.mft_attribute_header = self.__extract_mft_header__()
        print("[STANDARD INFORMATION]", self.mft_attribute_header)

        # ATTRIBUTE THỨ HAI - FILE NAME
        self.current_offset += self.mft_attribute_header["Attribute length"]
        self.drive.seek(self.current_offset)
        self.mft_entry_raw_data = self.drive.read(16)
        self.mft_attribute_header = self.__extract_mft_header__()
        print("[FILE NAME HEADER]", self.mft_attribute_header)

        if self.mft_attribute_header["Flag"] == "Resident":
            self.current_offset += 16
            self.drive.seek(self.current_offset)

            self.mft_entry_raw_data = self.drive.read(6)
            self.mft_entry_data = {
                "SIZE OF CONTENT": int.from_bytes(self.mft_entry_raw_data[0:4], byteorder=sys.byteorder),
                "OFFSET TO CONTENT": int.from_bytes(self.mft_entry_raw_data[4:6], byteorder=sys.byteorder),
            }

            self.current_offset += self.mft_entry_data["OFFSET TO CONTENT"] - 16
            self.drive.seek(self.current_offset)

            body = self.drive.read(self.mft_entry_data["SIZE OF CONTENT"])

            self.mft_entry_data = {
                "PARENT ID": int.from_bytes(body[0:6], byteorder=sys.byteorder),
                "NAME LENGTH": body[64],
                # không hiểu số 66 từ đâu ra nhưng thêm vào thì nó chạy đúng
                "FILE NAME": body[66:66 + body[64] * 2].decode("utf-16"),
            }

            print("[FILE NAME]", self.mft_entry_data)
        else:
            print("Non-resident")
        print()
        # debug
        time.sleep(2)
        self.current_mft_index_entry += 1

    def __extract_mft_header__(self) -> dict:
        header = {
            "Attribute type": int.from_bytes(self.mft_entry_raw_data[0:4], byteorder=sys.byteorder),
            "Attribute length": int.from_bytes(self.mft_entry_raw_data[4:8], byteorder=sys.byteorder),
            "Flag": "Resident" if int.from_bytes(self.mft_entry_raw_data[8:9], byteorder=sys.byteorder) == 0 else "Non-resident",
            "Name size": int.from_bytes(self.mft_entry_raw_data[9:10], byteorder=sys.byteorder),
            "Offset to name": int.from_bytes(self.mft_entry_raw_data[10:12], byteorder=sys.byteorder),
            "Attribute name": self.__get_attribute_type__(int.from_bytes(self.mft_entry_raw_data[0:4], byteorder=sys.byteorder)),
        }
        return header

    def __get_attribute_type__(self, attribute_type: int) -> str:
        for key, value in MFT_ATTRIBUTE_TYPE.items():
            if attribute_type == value:
                return key
        return "Unknown"

    def __get_entry_flags__(self, entry_flags: int) -> str:
        for key, value in MFT_ENTRY_FLAGS.items():
            if entry_flags == value:
                return key
        return "Unknown flags"

    def __get_file_attribute_flags__(self, file_attribute: int) -> str:
        for key, value in FILE_ATTRIBUTE_FLAGS.items():
            if file_attribute & value != 0:
                return key

        return "Unknown flags"
    # for debug

    def print_raw_mft(self, data) -> None:
        str_data = binascii.hexlify(data).decode("utf-8")

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

    def print_raw_bpb(self) -> None:
        str_data = binascii.hexlify(self.raw_data[0:BPS_SIZE]).decode("utf-8")

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
