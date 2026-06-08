import xmltodict
import json
import logging

logger = logging.getLogger(__name__)


def json_to_xml(json_data: dict, root_name: str = "root") -> str:
    try:
        xml_str = xmltodict.unparse({root_name: json_data}, pretty=True, short_empty_elements=True)
        logger.info(f"JSON converted to XML (root: {root_name})")
        return xml_str
    except Exception as e:
        logger.error(f"Failed to convert JSON to XML: {e}")
        raise


def xml_to_json(xml_str: str) -> dict:
    try:
        json_data = xmltodict.parse(xml_str)
        logger.info("XML converted to JSON")
        return json_data
    except Exception as e:
        logger.error(f"Failed to convert XML to JSON: {e}")
        raise
