#!/usr/bin/env python3.9

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from p1parser.tokens import (
    token,
    host,
    orgid,
)
bucket = "dummy"

client = InfluxDBClient(
    url=host,
    token=token,
    org=orgid,
    verify_ssl=False,
)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()




p = Point("my_measurement").tag("location", "atelier").field("temperature", 25.3)
write_api.write(bucket=bucket, record=p)