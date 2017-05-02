import argparse
import unittest
import mock
import six

from dogen.generator import Generator
from dogen.errors import Error
from dogen.tools import Tools

class TestURL(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None, params={})
        self.generator = Generator(self.log, args)

    def test_local_file(self):
        self.assertFalse(Tools.is_url("a_file.tmp"))

    def test_remote_http_file(self):
        self.assertTrue(Tools.is_url("http://host/file.tmp"))

    def test_remote_https_file(self):
        self.assertTrue(Tools.is_url("https://host/file.tmp"))

class TestFetchFile(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None, params={})
        self.generator = Generator(self.log, args)

    @mock.patch('dogen.generator.requests.get')
    def test_fetching_with_filename(self, mock_requests):
        def iter_content(**args):
            return ["file-content"]

        mock_requests.return_value.status_code = 200
        mock_requests.return_value.iter_content = iter_content

        with mock.patch.object(six.moves.builtins, 'open', mock.mock_open()) as mock_file:
            self.assertEqual(self.generator._fetch_file("https://host/file.tmp", "some-file"), "some-file")
            mock_requests.assert_called_with('https://host/file.tmp', verify=None, stream=True)
            mock_file().write.assert_called_once_with("file-content")

        self.log.info.assert_any_call("Fetching 'https://host/file.tmp' file...")
        self.log.info.assert_any_call("Fetched file will be saved as 'some-file'...")


    @mock.patch('dogen.generator.tempfile.mktemp', return_value="tmpfile")
    @mock.patch('dogen.generator.requests.get')
    def test_fetching_with_tmpfile(self, mock_requests, mock_tempfile):
        def iter_content(**args):
            return ["file-content"]

        mock_requests.return_value.status_code = 200
        mock_requests.return_value.iter_content = iter_content

        with mock.patch.object(six.moves.builtins, 'open', mock.mock_open()) as mock_file:
            self.assertEqual(self.generator._fetch_file("https://host/file.tmp"), "tmpfile")
            mock_tempfile.assert_called_with("-dogen")
            mock_requests.assert_called_with('https://host/file.tmp', verify=None, stream=True)
            mock_file().write.assert_called_once_with("file-content")

        self.log.info.assert_any_call("Fetching 'https://host/file.tmp' file...")
        self.log.info.assert_any_call("Fetched file will be saved as 'tmpfile'...")

class TestCustomTemplateHandling(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template="http://host/custom-template", scripts_path=None,
                                  additional_script=None, skip_ssl_verification=None, params={})
        self.generator = Generator(self.log, args)

    def test_do_not_fail_if_no_template_is_provided(self):
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None, params={})
        self.generator = Generator(self.log, args)

        fetch_file_mock = mock.Mock()
        self.generator._fetch_file = fetch_file_mock

        self.assertEqual(self.generator.template, None)
        self.generator._handle_custom_template()
        fetch_file_mock.assert_not_called()
        self.assertEqual(self.generator.template, None)

    @mock.patch('dogen.generator.os.path.exists', return_value=True)
    def test_fetch_template_success(self, mock_path):
        fetch_file_mock = mock.Mock(return_value="some-tmp-file")
        self.generator._fetch_file = fetch_file_mock

        self.assertEqual(self.generator.template, "http://host/custom-template")
        self.generator._handle_custom_template()
        fetch_file_mock.assert_called_with("http://host/custom-template")
        self.assertEqual(self.generator.template, "some-tmp-file")

    @mock.patch('dogen.generator.os.path.exists', return_value=False)
    def test_fetch_template_with_error(self, mock_path):
        fetch_file_mock = mock.Mock(return_value="some-tmp-file")
        self.generator._fetch_file = fetch_file_mock

        self.assertEqual(self.generator.template, "http://host/custom-template")

        with self.assertRaises(Error) as cm:
            self.generator._handle_custom_template()

        self.assertEquals(str(cm.exception), "Template file 'some-tmp-file' could not be found. Please make sure you specified correct path or check if the file was successfully fetched.")

        fetch_file_mock.assert_called_with("http://host/custom-template")
        self.assertEqual(self.generator.template, "some-tmp-file")
