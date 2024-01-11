import re
import pytz

import dateutil.parser as date_parser


class AWSManifestNormalizer:
    def __init__(self, manifest, version, path):
        self.manifest = manifest
        self.version = version
        self.path = path

        self.normalizer = self.picker(self.version)

    def picker(self, version):
        return {
            "v1": self.normalize_v1,
            "v2": self.normalize_v2,
        }[version]

    def normalize(self):
        return self.normalizer()

    def normalize_v1(self):
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
            {
                "name": f"{column['category']}_{re.sub(':', '_', column['name'])}",
                "type": type_mapping.get(
                    column.get("type", "String")
                ),  # old manifests don't have a type
            }
            for column in self.manifest["columns"]
        ]

        manifest = {
            "billing_period": date_parser.parse(
                self.manifest["billingPeriod"]["start"]
            ).replace(day=1),
            "execution_id": self.manifest["assemblyId"],
            "data_files": self.manifest["reportKeys"],
            "columns": columns,
        }

        return manifest

    def normalize_v2(self):
        v2_pattern = r"BILLING_PERIOD=(\d{4}-\d{2})"

        manifest = {
            "billing_period": date_parser.parse(
                re.search(v2_pattern, self.path).group(1)
            ).replace(day=1, tzinfo=pytz.UTC),
            "execution_id": self.manifest["executionId"],
            "data_files": self.manifest["dataFiles"],
            "columns": self.manifest["columns"],
        }

        return manifest
