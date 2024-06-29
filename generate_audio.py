from enum import Enum
import os
import json
import requests
import ffmpeg
import argparse
import subprocess, sys

# APIサーバーのURL
API_SERVER = "http://127.0.0.1:50032"

# 音声合成時に使用するパラメータのデフォルト値
DEFAULT_PARAMS = {
    "speedScale": 1.0,
    "volumeScale": 1.0,
    "prosodyDetail": [],
    "pitchScale": 0.0,
    "intonationScale": 1.0,
    "prePhonemeLength": 0.1,
    "postPhonemeLength": 0.5,
    "outputSamplingRate": 24000,
}


class Position(Enum):
    """
    聞く人に対する音声の位置
    """

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


def parse_arguments():
    """
    コマンドライン引数を解析する
    """
    parser = argparse.ArgumentParser(
        description="COEIROINKのAPIを利用してテキストファイルから合成音声を作成する"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="scenario.txt",
        help="入力元テキストファイル",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="audio.wav",
        help="出力先パス",
    )
    parser.add_argument(
        "--speakerUuid",
        type=str,
        default="297a5b91-f88a-6951-5841-f1e648b2e594",
        help="デフォルトのスピーカーUUID",
    )
    parser.add_argument(
        "--styleId", type=int, default=33, help="デフォルトのスタイルID"
    )
    parser.add_argument("--play", action="store_true", help="音声作成後に再生する")

    return parser.parse_args()


def synthesis(text: str, speaker_uuid: str, style_id: int, params):
    """
    文字列を音声化する
    """
    query = {
        "speakerUuid": speaker_uuid,
        "styleId": style_id,
        "text": text,
        **params,
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


def edit_position(fname: str, position: Position):
    """
    音声の左右の位置を変更する
    """
    old_file = "old.wav"

    os.rename(fname, old_file)

    if position == position.LEFT:
        cp = subprocess.run(
            f'ffmpeg -i {old_file} -af pan="stereo|c0=2*c0|c1=0*c0" {fname}',
            shell=True,
            check=True,
        )
    elif position == position.RIGHT:
        cp = subprocess.run(
            f'ffmpeg -i {old_file} -af pan="stereo|c0=0*c0|c1=2*c0" {fname}',
            shell=True,
            check=True,
        )
    else:
        cp = subprocess.run(
            f'ffmpeg -i {old_file} -af pan="stereo|c0=1*c0|c1=1*c0" {fname}',
            shell=True,
            check=True,
        )
    if cp.returncode != 0:
        print("ls failed.", file=sys.stderr)
        sys.exit(1)

    os.remove(old_file)


if __name__ == "__main__":
    params = DEFAULT_PARAMS.copy()

    # コマンド引数を解析
    args = parse_arguments()

    current_speaker_uuid = args.speakerUuid
    current_style_id = args.styleId
    current_position = Position.CENTER
    input_file = args.input
    output_file = args.output

    with open(input_file, "r", encoding="utf-8") as f:
        count = 0
        for line in f:
            line = line.strip()

            # 終了
            if line == "<<end>>":
                break

            # 見出しやコメントをスキップ
            if line.startswith("#") or line.startswith("//") or line == "":
                continue

            # 無音区間の挿入
            if line == "<<silent>>":
                append_audio(output_file, "assets/silent.wav")
                continue

            # 任意の音声ファイルの挿入
            if line.startswith("<<audio"):
                audio_path = line.strip("<<>>").split(":")[1]
                append_audio(output_file, audio_path)
                continue

            # speed変更
            if line.startswith("<<speed"):
                speed = float(line.strip("<<>>").split(":")[1])
                params["speedScale"] = speed
                continue

            # scale変更
            if line.startswith("<<scale"):
                scale_params = line.strip("<<>>").split()[1:]
                for param in scale_params:
                    key, value = param.split(":")
                    params[key + "Scale"] = float(value)
                continue

            # SPEAKER_UUID変更
            if line.startswith("<<speakerUuid"):
                current_speaker_uuid = line.strip("<<>>").split(":")[1]
                continue

            # STYLE_ID変更
            if line.startswith("<<styleId"):
                current_style_id = int(line.strip("<<>>").split(":")[1])
                continue

            # ポジション変更
            if line.startswith("<<position"):
                current_position = Position(line.strip("<<>>").split(":")[1])
                continue

            # リセット
            if line == "<<reset>>":
                params = DEFAULT_PARAMS.copy()
                current_speaker_uuid = args.speakerUuid
                current_style_id = args.styleId
                current_position = Position.CENTER
                continue

            # テキストを音声化
            audio = synthesis(line, current_speaker_uuid, current_style_id, params)

            temp_file = "temp.wav"
            with open(temp_file, "wb") as f_temp:
                f_temp.write(audio)

            edit_position(temp_file, current_position)

            if count == 0:
                if os.path.exists(output_file):
                    os.remove(output_file)
                os.rename(temp_file, output_file)
            else:
                append_audio(output_file, temp_file)
                os.remove(temp_file)

            count += 1

    # 再生
    if args.play:
        cp = subprocess.run(
            f"ffplay {output_file}",
            shell=True,
            check=True,
        )
        if cp.returncode != 0:
            print("ls failed.", file=sys.stderr)
            sys.exit(1)
