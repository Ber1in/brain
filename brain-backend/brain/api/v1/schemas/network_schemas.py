# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from typing import List, Optional
from ipaddress import ip_interface
import re
from pydantic import BaseModel, Field, ConstrainedStr
from pydantic.validators import str_validator


class IPWithNetmask(str):
    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        # Check that both IP and netmask are provided
        values = value.split("/")
        if len(values) != 2:
            raise ValueError("Missing netmask. Format must be IP/MASK (e.g., 192.168.1.10/24)")

        # Ensure that the mask is given as number of bits, not a specific mask
        try:
            int(values[1])
        except ValueError:
            raise ValueError("Expects the number of mask bits, not the specific mask")

        # Validate the IP address format using ip_interface
        iface = ip_interface(value)
        # Ensure it is a host IP, not the network address
        if iface.ip == iface.network.network_address:
            raise ValueError("IP must be a host address, not the network address")

        return value

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            example="127.0.0.1/24",
            format="ip-netmask",
            description="IP/Netmask (support IPv4/IPv6)"
        )


class Mac(ConstrainedStr):
    regex = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

    @classmethod
    def validate(cls, value: str):
        value = value.replace("-", ":").lower()
        if not cls.regex.match(value):
            raise ValueError(
                f"Invalid MAC address format: '{value}'. Must be in the form of 'XX:XX:XX:XX:XX:XX'"
                " or 'XX-XX-XX-XX-XX-XX' (e.g. '00:1A:2B:3C:4D:5E')"
            )
        # Reject all-zeros or all-FF (case-insensitive)
        if value in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
            raise ValueError(f"Disallowed MAC address: '{value}' (cannot be all 0s or all Fs)")
        return value


class InterfaceCreate(BaseModel):
    mv200_id: str = Field(..., description="Target SoC ID to perform network operation")
    ip: IPWithNetmask = Field(..., description="IP address with CIDR mask, e.g., 192.168.1.10/24")
    vlan_tag: int = Field(..., description="VLAN tag for the interface")
    gateway: str = Field(..., description="Gateway address for the interface")
    mtu: int = Field(1500, description="Optional field, MTU size", example=1500)
    mac: Optional[Mac] = Field(None, description="MAC address of the interface (optional)")
    dns: Optional[List[str]] = Field(None, description="List of DNS server addresses (optional)")
    description: Optional[str] = Field(None, description="Description of the network interface")


class InterfaceUpdate(BaseModel):
    """Schema for updating only the description of an interface"""
    id: str = Field(..., description="Unique ID of the interface to update")
    description: Optional[str] = Field(None, description="New description for the interface")


class InterfaceDelete(BaseModel):
    """Schema for deleting an existing interface"""
    mv200_id: str = Field(..., description="Target SoC ID to perform network operation")
    id: str = Field(..., description="Unique ID of the network interface to delete")


class InterfaceInfo(InterfaceCreate):
    """Schema for returning interface info"""
    id: str = Field(..., description="Unique ID of the network interface")
    ifname: str = Field(None)
