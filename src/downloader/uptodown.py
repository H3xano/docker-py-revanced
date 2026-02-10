"""Upto Down Downloader."""

from typing import Any, Self

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger

from src.app import APP
from src.downloader.download import Downloader
from src.exceptions import UptoDownAPKDownloadError
from src.utils import bs4_parser, handle_request_response, request_header, request_timeout


class UptoDown(Downloader):
    """Files downloader."""

    def extract_download_link(self: Self, page: str, app: str) -> tuple[str, str]:
        """Extract download link from uptodown url."""
        r = requests.get(page, headers=request_header, allow_redirects=True, timeout=request_timeout)
        handle_request_response(r, page)
        soup = BeautifulSoup(r.text, bs4_parser)
        detail_download_button = soup.find("button", id="detail-download-button")

        if not isinstance(detail_download_button, Tag):
            logger.error(f"Could not find detail-download-button on page: {page}")
            msg = f"Unable to download {app} from uptodown."
            raise UptoDownAPKDownloadError(msg, url=page)

        data_url = detail_download_button.get("data-url")
        
        if not data_url:
            logger.error(f"data-url attribute missing from button on page: {page}")
            msg = f"Unable to retrieve data-url for {app} from uptodown."
            raise UptoDownAPKDownloadError(msg, url=page)
            
        download_url = f"https://dw.uptodown.com/dwn/{data_url}"
        logger.debug(f"Final download URL: {download_url}")
        
        file_name = f"{app}.apk"
        self._download(download_url, file_name)

        return file_name, download_url

    def specific_version(self: Self, app: APP, version: str) -> tuple[str, str]:
        """Function to download the specified version of app from uptodown.

        :param app: Name of the application
        :param version: Version of the application to download
        :return: Version of downloaded apk
        """
        logger.debug("downloading specified version of app from uptodown.")
        url = f"{app.download_source}/versions"
        html = requests.get(url, headers=request_header, timeout=request_timeout).text
        soup = BeautifulSoup(html, bs4_parser)
        detail_app_name = soup.find("h1", id="detail-app-name")

        if not isinstance(detail_app_name, Tag):
            msg = f"Unable to download {app} from uptodown."
            raise UptoDownAPKDownloadError(msg, url=url)

        app_code = detail_app_name.get("data-code")
        version_page = 1
        download_url = None
        version_found = False

        while not version_found:
            version_url = f"{app.download_source}/apps/{app_code}/versions/{version_page}"
            r = requests.get(version_url, headers=request_header, timeout=request_timeout)
            handle_request_response(r, version_url)
            json = r.json()

            if "data" not in json:
                break

            for item in json["data"]:
                if item["version"] == version:
                    version_url_val = item["versionURL"]
                    if isinstance(version_url_val, dict):
                        base_url = version_url_val.get("url")
                        extra = version_url_val.get("extraURL")
                        ver_id = version_url_val.get("versionID")
                        
                        if not all([base_url, extra, ver_id]):
                            logger.error(f"Incomplete versionURL data for {app}: {version_url_val}")
                            continue
                            
                        download_url = f"{base_url}/{extra}/{ver_id}-x"
                    else:
                        download_url = f"{version_url_val}-x"
                        
                    if not download_url.startswith("http"):
                         logger.error(f"Invalid download URL constructed: {download_url}")
                         continue

                    logger.debug(f"Constructed download URL: {download_url}")
                    version_found = True
                    break

            version_page += 1

        if download_url is None:
            msg = f"Unable to download {app.app_name} from uptodown."
            raise UptoDownAPKDownloadError(msg, url=url)

        return self.extract_download_link(download_url, app.app_name)

    def latest_version(self: Self, app: APP, **kwargs: Any) -> tuple[str, str]:
        """Function to download the latest version of app from uptodown."""
        logger.debug("downloading latest version of app from uptodown.")
        page = f"{app.download_source}/download"
        return self.extract_download_link(page, app.app_name)
