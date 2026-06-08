"""
E2E functional test for Django To-Do list app deployed at 8.149.137.130
Uses Selenium in headless Chrome mode.

Test cases:
  Step A: Home page - verify title, h1, no 404 static resources
  Step B: Create list - add "Wake up" and "Hit the gym", verify list content and URL
  Step C: User isolation - new session, verify empty list, add "play soccer", verify different URL
  Step D: Data persistence - revisit URL_1, verify old items, add "Study", verify 3 items
"""

import time
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


SITE_URL = "http://8.149.137.130"


def create_driver():
    """Create a headless Chrome driver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


class TodoListE2ETest(unittest.TestCase):

    def setUp(self):
        self.driver = create_driver()
        self.driver.implicitly_wait(3)
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        self.driver.quit()

    def _add_item(self, text):
        """Helper: type text into the input box and submit, then wait for page to update."""
        input_box = self.wait.until(
            EC.presence_of_element_located((By.ID, "id_new_item"))
        )
        input_box.clear()
        input_box.send_keys(text)
        input_box.send_keys(Keys.ENTER)
        # Wait for the new item to appear in the table
        time.sleep(1)
        self.wait.until(
            lambda d: text in d.find_element(By.ID, "id_list_table").text
        )

    def _check_no_404_static(self):
        """Check browser logs for 404 on static resources."""
        logs = self.driver.get_log("browser")
        failed_resources = []
        for entry in logs:
            msg = entry.get("message", "")
            if "404" in msg and ("static" in msg or ".css" in msg or ".js" in msg):
                failed_resources.append(msg)
        if failed_resources:
            self.fail(f"404 static resources found:\n" + "\n".join(failed_resources))

    def _get_table_rows(self):
        """Get all row texts from the list table."""
        table = self.wait.until(
            EC.presence_of_element_located((By.ID, "id_list_table"))
        )
        rows = table.find_elements(By.TAG_NAME, "tr")
        return [r.text for r in rows]

    # ============================================================
    # Step A: Home page
    # ============================================================
    def test_step_a_home_page(self):
        print("\n=== Step A: Home Page ===")
        self.driver.get(SITE_URL)

        h1 = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        print(f"  h1 text: '{h1.text}'")
        self.assertEqual(h1.text, "Start a new To-Do list")

        self._check_no_404_static()
        print("  No 404 static resources - OK")

    # ============================================================
    # Step B: Create list with "Wake up" and "Hit the gym"
    # ============================================================
    def test_step_b_create_list(self):
        print("\n=== Step B: Create List ===")
        self.driver.get(SITE_URL)

        # Add "Wake up"
        self._add_item("Wake up")

        # Verify h1 changed to "Your To-Do list"
        h1 = self.driver.find_element(By.TAG_NAME, "h1")
        print(f"  After 'Wake up' - h1: '{h1.text}', URL: {self.driver.current_url}")

        # Add "Hit the gym"
        self._add_item("Hit the gym")

        # Verify h1
        h1 = self.driver.find_element(By.TAG_NAME, "h1")
        print(f"  After 'Hit the gym' - h1: '{h1.text}'")
        self.assertEqual(h1.text, "Your To-Do list")

        # Verify table rows
        row_texts = self._get_table_rows()
        print(f"  Table rows: {row_texts}")
        self.assertIn("1", row_texts[0])
        self.assertIn("Wake up", row_texts[0])
        self.assertIn("2", row_texts[1])
        self.assertIn("Hit the gym", row_texts[1])

        # Verify URL is not root
        current_url = self.driver.current_url
        print(f"  URL_1: {current_url}")
        self.assertNotEqual(current_url.rstrip("/"), SITE_URL)
        self.assertIn("/lists/", current_url)

        # Save URL for later steps
        TodoListE2ETest.url_1 = current_url

    # ============================================================
    # Step C: User isolation
    # ============================================================
    def test_step_c_user_isolation(self):
        print("\n=== Step C: User Isolation ===")
        self.driver.delete_all_cookies()
        self.driver.get(SITE_URL)

        h1 = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        print(f"  h1 text: '{h1.text}'")
        self.assertEqual(h1.text, "Start a new To-Do list")

        # Verify table is empty or not present
        tables = self.driver.find_elements(By.ID, "id_list_table")
        if tables:
            rows = tables[0].find_elements(By.TAG_NAME, "tr")
            self.assertEqual(len(rows), 0, f"Expected empty table but found: {[r.text for r in rows]}")
        print("  Table is empty - OK")

        # Add "play soccer"
        self._add_item("play soccer")

        url_2 = self.driver.current_url
        print(f"  URL_2: {url_2}")
        self.assertIn("/lists/", url_2)
        self.assertNotEqual(url_2, TodoListE2ETest.url_1)
        print("  URL_2 != URL_1 - OK")

        TodoListE2ETest.url_2 = url_2

    # ============================================================
    # Step D: Data persistence
    # ============================================================
    def test_step_d_data_persistence(self):
        print("\n=== Step D: Data Persistence ===")
        self.driver.get(TodoListE2ETest.url_1)

        h1 = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        print(f"  h1 text: '{h1.text}'")
        self.assertEqual(h1.text, "Your To-Do list")

        row_texts = self._get_table_rows()
        print(f"  Table rows: {row_texts}")
        self.assertTrue(any("Wake up" in r for r in row_texts))
        self.assertTrue(any("Hit the gym" in r for r in row_texts))

        # Add "Study"
        self._add_item("Study")

        row_texts = self._get_table_rows()
        print(f"  Table rows after 'Study': {row_texts}")
        self.assertEqual(len(row_texts), 3)
        self.assertIn("1", row_texts[0])
        self.assertIn("2", row_texts[1])
        self.assertIn("3", row_texts[2])
        print("  3 items with correct sequence numbers - OK")


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(TodoListE2ETest("test_step_a_home_page"))
    suite.addTest(TodoListE2ETest("test_step_b_create_list"))
    suite.addTest(TodoListE2ETest("test_step_c_user_isolation"))
    suite.addTest(TodoListE2ETest("test_step_d_data_persistence"))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        for failure in result.failures:
            print(f"\nFAILED: {failure[0]}")
            print(failure[1])
        for error in result.errors:
            print(f"\nERROR: {error[0]}")
            print(error[1])
    print("=" * 60)
