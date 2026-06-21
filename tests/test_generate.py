import datetime
from unittest.mock import patch
from src import generate, recommender


def _rec():
    return recommender.Recommendation(
        places=[
            recommender.Place("서울숲", "사슴 먹이주기", "35분", "25분"),
            recommender.Place("길동생태공원", "곤충 관찰", "20분", "10분"),
            recommender.Place("어린이대공원", "동물원", "40분", "30분"),
        ],
        weather="주말 흐림.",
        prep="간식·물.",
    )


def test_today_kst_returns_date():
    assert isinstance(generate.today_kst(), datetime.date)


def test_run_dry_run_prints_and_does_not_send(capsys):
    with patch("src.generate.history.load_recent", return_value=[]), \
         patch("src.generate.recommender.generate_recommendation", return_value=_rec()), \
         patch("src.generate.anthropic.Anthropic"), \
         patch("src.generate.telegram.send_message") as mock_send, \
         patch("src.generate.history.append_entry") as mock_append:
        generate.run(dry_run=True)
    out = capsys.readouterr().out
    assert "서울숲" in out
    mock_send.assert_not_called()
    mock_append.assert_not_called()


def test_run_prepends_permanent_excludes_to_avoid():
    with patch("src.generate.history.load_recent", return_value=["과거장소"]), \
         patch("src.generate.recommender.generate_recommendation", return_value=_rec()) as mock_gen, \
         patch("src.generate.anthropic.Anthropic"), \
         patch("src.generate.config.load_secrets",
               return_value={"telegram_token": "tok", "telegram_chat_id": "chat"}), \
         patch("src.generate.telegram.send_message"), \
         patch("src.generate.history.append_entry"):
        generate.run(dry_run=False)
    avoid = mock_gen.call_args.kwargs["avoid"]
    assert "올림픽공원" in avoid
    assert "과거장소" in avoid


def test_run_sends_and_records_on_success():
    with patch("src.generate.history.load_recent", return_value=["과거장소"]), \
         patch("src.generate.recommender.generate_recommendation", return_value=_rec()), \
         patch("src.generate.anthropic.Anthropic"), \
         patch("src.generate.config.load_secrets",
               return_value={"telegram_token": "tok", "telegram_chat_id": "chat"}), \
         patch("src.generate.telegram.send_message") as mock_send, \
         patch("src.generate.history.append_entry") as mock_append:
        generate.run(dry_run=False)
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "tok"
    assert mock_append.call_count == 3  # 3곳 모두 기록
    recorded = [c.args[2] for c in mock_append.call_args_list]
    assert recorded == ["서울숲", "길동생태공원", "어린이대공원"]


def test_run_sends_failure_message_after_retries():
    with patch("src.generate.history.load_recent", return_value=[]), \
         patch("src.generate.recommender.generate_recommendation",
               side_effect=RuntimeError("boom")) as mock_gen, \
         patch("src.generate.anthropic.Anthropic"), \
         patch("src.generate.config.load_secrets",
               return_value={"telegram_token": "tok", "telegram_chat_id": "chat"}), \
         patch("src.generate.telegram.send_message") as mock_send, \
         patch("src.generate.history.append_entry") as mock_append:
        generate.run(dry_run=False)
    assert mock_gen.call_count == 2  # 1회 재시도
    sent_text = mock_send.call_args[0][2]
    assert "실패" in sent_text
    mock_append.assert_not_called()  # 실패 시 기록 안 함
