import json
import requests

api_server = "http://127.0.0.1:50032"


def save_speakers():
    """
    利用可能なSpeaker情報をファイル出力する
    """
    speakers = []

    response = requests.get(
        f"{api_server}/v1/speakers",
    )

    for item in json.loads(response.content):
        speaker = {
            "speakerName": item["speakerName"],
            "speakerUuid": item["speakerUuid"],
            "styles": [
                {"styleName": style["styleName"], "styleId": style["styleId"]}
                for style in item["styles"]
            ],
            "version": item["version"],
        }

        speakers.append(speaker)

    # 出力ファイルに保存
    with open("speakers.json", "w", encoding="utf-8") as f:
        json.dump(speakers, f, ensure_ascii=False, indent=4)


save_speakers()
