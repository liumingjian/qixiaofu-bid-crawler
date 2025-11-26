import time
import unittest

from core.scheduler import CrawlScheduler, SchedulerConfig


class DummyController:
    def __init__(self) -> None:
        self.started = 0
        self.force_running = False

    def start(self) -> bool:
        if self.force_running:
            return False
        self.started += 1
        return True


class CrawlSchedulerTest(unittest.TestCase):
    def test_interval_scheduler_triggers_controller(self) -> None:
        controller = DummyController()
        cfg = SchedulerConfig(enabled=True, interval_minutes=0.001)
        scheduler = CrawlScheduler(controller, cfg)
        scheduler.start()
        time.sleep(0.2)
        scheduler.stop()
        self.assertGreaterEqual(controller.started, 1)

    def test_scheduler_skips_when_controller_busy(self) -> None:
        controller = DummyController()
        controller.force_running = True
        cfg = SchedulerConfig(enabled=True, interval_minutes=0.001)
        scheduler = CrawlScheduler(controller, cfg)
        scheduler.start()
        time.sleep(0.05)
        scheduler.stop()
        self.assertEqual(controller.started, 0)

    def test_cron_expression_generates_wait_time(self) -> None:
        controller = DummyController()
        cfg = SchedulerConfig(enabled=True, cron="*/5 * * * *", timezone="UTC")
        scheduler = CrawlScheduler(controller, cfg)
        wait = scheduler._next_interval_seconds()
        self.assertGreater(wait, 0)


if __name__ == "__main__":
    unittest.main()
