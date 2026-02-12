"""
Slack 알림 모듈
━━━━━━━━━━━━━━
데이터 품질 검증 결과를 Slack Webhook으로 전송합니다.

사용법:
  1. Slack App 생성 → Incoming Webhook URL 발급
  2. .env 파일에 SLACK_WEBHOOK_URL 설정
  3. python 07_data_quality/slack_alert.py
"""

import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
REPORT_DIR = Path(__file__).parent / "reports"


def send_slack_alert(report: dict | None = None):
    """
    품질 검증 결과를 Slack으로 전송
    
    Args:
        report: run_quality_checks()의 반환값. None이면 최신 리포트 파일에서 로드
    """
    # 리포트 로드
    if report is None:
        report_files = sorted(REPORT_DIR.glob("quality_report_*.json"))
        if not report_files:
            print("❌ 리포트 파일이 없습니다. 먼저 품질 검증을 실행하세요.")
            return
        with open(report_files[-1]) as f:
            report = json.load(f)
    
    # Slack 메시지 구성
    quality_score = report["quality_score"]
    passed = report["passed"]
    failed = report["failed"]
    total = report["total_checks"]
    
    # 색상 결정
    if quality_score >= 90:
        color = "#1CB875"  # 녹색
        status_emoji = "✅"
    elif quality_score >= 70:
        color = "#FFB800"  # 노란색
        status_emoji = "⚠️"
    else:
        color = "#F04438"  # 빨간색
        status_emoji = "🔴"
    
    # 실패한 검증 목록
    failed_checks = [r for r in report["results"] if not r["passed"]]
    failed_text = ""
    if failed_checks:
        failed_items = []
        for check in failed_checks:
            severity_icon = "🔴" if check["severity"] == "critical" else "🟡"
            failed_items.append(f"{severity_icon} `{check['check_name']}`: {check['details']}")
        failed_text = "\n".join(failed_items)
    
    # Slack Block Kit 메시지
    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{status_emoji} QuickPay 데이터 품질 리포트",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*품질 점수*\n{quality_score}%"},
                            {"type": "mrkdwn", "text": f"*검증 결과*\n✅ {passed} / ❌ {failed} / 전체 {total}"},
                            {"type": "mrkdwn", "text": f"*실행 시각*\n{report['run_timestamp'][:19]}"},
                            {"type": "mrkdwn", "text": f"*환경*\nDuckDB (dev)"},
                        ]
                    },
                ]
            }
        ]
    }
    
    # 실패 항목이 있으면 추가
    if failed_text:
        payload["attachments"][0]["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*❌ 실패한 검증:*\n{failed_text}"
            }
        })
    
    # 액션 버튼
    payload["attachments"][0]["blocks"].append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "📊 상세 리포트 보기"},
                "url": "http://localhost:8080/data_docs"  # GE Data Docs URL
            }
        ]
    })
    
    # Webhook 전송
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URL이 설정되지 않았습니다.")
        print("   .env 파일에 SLACK_WEBHOOK_URL=https://hooks.slack.com/... 을 추가하세요.\n")
        print("📤 전송 예정 메시지 (미리보기):")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            print(f"✅ Slack 알림 전송 완료! (품질 점수: {quality_score}%)")
        else:
            print(f"❌ Slack 전송 실패: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Slack 전송 에러: {e}")


def send_anomaly_alert(metric_name: str, current_value: float, expected_value: float, zscore: float):
    """
    특정 지표 이상 탐지 시 Slack 알림
    
    Args:
        metric_name: 지표명 (예: "DAU", "GMV")
        current_value: 현재 값
        expected_value: 기대 값 (평균)
        zscore: Z-score
    """
    direction = "📈 급증" if zscore > 0 else "📉 급감"
    change_pct = round((current_value - expected_value) / expected_value * 100, 1)
    
    payload = {
        "text": (
            f"🚨 *지표 이상 탐지 - {metric_name}*\n"
            f">{direction} | 현재: {current_value:,.0f} | 기대: {expected_value:,.0f}\n"
            f">변동: {change_pct:+.1f}% | Z-score: {zscore:.2f}\n"
            f">시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    }
    
    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        print(f"✅ 이상 탐지 알림 전송: {metric_name}")
    else:
        print(f"📤 이상 탐지 알림 (미리보기):\n{payload['text']}")


if __name__ == "__main__":
    send_slack_alert()
