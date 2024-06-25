import os
import json
import requests
import ffmpeg


API_SERVER = "http://127.0.0.1:50032"
INPUT_FILE = "scenario.txt"
OUTPUT_FILE = "audio.wav"
SPEAKER_UUID = "3c37646f-3881-5374-2a83-149267990abc"
STYLE_ID = 0


def synthesis(text: str):
    """
    文字列を音声化する
    """
    query = {
        "speakerUuid": SPEAKER_UUID,
        "styleId": STYLE_ID,
        "text": text,
        "speedScale": 1.0,
        "volumeScale": 1.0,
        "prosodyDetail": [],
        "pitchScale": 0.0,
        "intonationScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.5,
        "outputSamplingRate": 24000,
    }

    # 音声合成を実行
    response = requests.post(
        f"{API_SERVER}/v1/synthesis",
        headers={"Content-Type": "application/json"},
        data=json.dumps(query),
    )
    response.raise_for_status()

    return response.content


def append_audio(audio1: str, audio2: str):
    """
    audio1の後ろにaudio2を結合する
    """
    old_file = "old.wav"
    os.rename(audio1, old_file)
    (
        ffmpeg.concat(ffmpeg.input(old_file), ffmpeg.input(audio2), v=0, a=1)
        .output(audio1)
        .run()
    )
    os.remove(old_file)


if __name__ == "__main__":
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        count = 0
        for line in f:
            line = line.strip()

            # 見出しやコメントをスキップ
            if line.startswith("#") or line.startswith("//") or line == "":
                continue

            # 無音区間の挿入
            if line == "<<silent>>":
                append_audio(OUTPUT_FILE, "assets/silent.wav")
                continue

            # テキストを音声化
            audio = synthesis(line)

            if count == 0:
                with open(OUTPUT_FILE, "wb") as f_temp:
                    f_temp.write(audio)
            else:
                temp_file = "temp.wav"
                with open(temp_file, "wb") as f_temp:
                    f_temp.write(audio)
                append_audio(OUTPUT_FILE, temp_file)
                os.remove(temp_file)

            count += 1
