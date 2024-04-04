import re
import pytz

import dateutil.parser as date_parser
from open_finops import ManifestObject, Column


class AWSManifestNormalizer:
    def __init__(self, manifest, version, path):
        self.manifest = manifest
        self.version = version
        self.path = path

    def normalize(self) -> ManifestObject:
        if self.version not in ["v1", "v2"]:
            raise ValueError(f"Invalid CUR version: {self.version}")
        if self.version == "v1":
            return self.normalize_v1()
        elif self.version == "v2":
            return self.normalize_v2()

    def normalize_v1(self) -> ManifestObject:
        type_mapping = {
            "String": "String",
            "Interval": "String",
            "DateTime": "DateTime",
            "Decimal": "Decimal(20, 8)",
            "BigDecimal": "Decimal(20, 8)",
            "OptionalBigDecimal": "Decimal(20, 8)",
            "OptionalString": "String",
        }

        columns = [
            Column(
                name=f"{column['category']}_{re.sub(':', '_', column['name'])}",
                type=type_mapping.get(column.get("type", "String")),
            )
            for column in self.manifest["columns"]
        ]
        billing_period = date_parser.parse(
            self.manifest["billingPeriod"]["start"]
        ).replace(day=1)
        manifest = ManifestObject(
            billing_period=billing_period,
            execution_id=self.manifest["assemblyId"],
            data_files=self.manifest["reportKeys"],
            columns=columns,
            vendor="aws",
            version="v1",
        )

        return manifest

    def normalize_v2(self) -> ManifestObject:
        v2_pattern = r"BILLING_PERIOD=(\d{4}-\d{2})"

        data_files = ["/".join(f.split("/")[3:]) for f in self.manifest["dataFiles"]]

        type_mapping = {
            "string": "String",
            "timestamp": "DateTime64(9)",
            "double": "Float64",
            "map": "Map(String, Nullable(String))",
            "struct": "Tuple(edp_discount Nullable(String))",
        }

        columns = [
            {
                "name": column["name"],
                "type": type_mapping.get(
                    column.get("type", "String")
                ),  # old manifests don't have a type
            }
            for column in self.manifest["columns"]
        ]
        billing_period = date_parser.parse(
            re.search(v2_pattern, self.path).group(1)
        ).replace(day=1, tzinfo=pytz.UTC)
        manifest = ManifestObject(
            billing_period=billing_period,
            execution_id=self.manifest["executionId"],
            data_files=data_files,
            columns=columns,
            vendor="aws",
            version="v2",
        )

        return manifest
