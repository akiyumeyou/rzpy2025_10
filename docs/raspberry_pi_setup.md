# ラズベリーパイ移植手順書

## 概要

このドキュメントは、高齢者向け安否確認システムをRaspberry Pi上で動作させるための設定手順をまとめたものです。コードの修正は不要で、環境設定と認証情報の配置のみで動作します。

---

## 前提条件

### ハードウェア要件
- **Raspberry Pi**: Raspberry Pi 4 または 5（推奨：4GB RAM以上）
- **OS**: Raspberry Pi OS (64-bit推奨)
- **マイク**: USBマイクまたはオーディオハット対応マイク
- **スピーカー**: USB/3.5mmジャック/HDMIオーディオ
- **インターネット**: 有線または無線LAN接続（必須）

### ソフトウェア要件
- Python 3.10以上（Raspberry Pi OSにプリインストール）
- pip（パッケージマネージャー）
- git（ソースコード取得用）

---

## セットアップ手順

### 1. システムアップデート

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. 必要なシステムパッケージのインストール

```bash
# オーディオ処理関連
sudo apt install -y portaudio19-dev python3-pyaudio

# 音楽プレイヤー（simple_voice_chat.pyで使用）
sudo apt install -y mpg123

# 開発ツール（requirements.txtのビルドに必要）
sudo apt install -y python3-dev build-essential
```

### 3. プロジェクトのクローン

```bash
cd ~
git clone <あなたのリポジトリURL> rzpy2025_10
cd rzpy2025_10
```

### 4. Python仮想環境の作成

```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Python依存パッケージのインストール

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**注意**: PyAudioのインストールでエラーが出る場合は、以下を試してください：
```bash
sudo apt install -y python3-pyaudio
pip install pyaudio --global-option="build_ext" --global-option="-I/usr/include" --global-option="-L/usr/lib"
```

---

## 設定ファイルと認証情報

### 6. 環境変数の設定（.envファイル）

プロジェクトルートに `.env` ファイルを作成します：

```bash
nano .env
```

以下の内容を記入してください：

```bash
# ========================================
# 必須設定
# ========================================

# OpenAI API キー（必須）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ユーザー情報
CARE_USER_NAME=利用者の名前

# ========================================
# オプション設定（Google Sheets連携）
# ========================================

# Google Spreadsheet ID
# 例: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit の部分
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here

# ========================================
# オプション設定（Gmail通知）
# ========================================

# Gmail アカウント（送信元）
GMAIL_USER=your_email@gmail.com

# 家族のメールアドレス（複数はカンマ区切り）
FAMILY_EMAILS=family1@example.com,family2@example.com

# Gmail OAuth2認証ファイルのパス（デフォルト: data/credentials.json）
GMAIL_CLIENT_SECRET_PATH=data/credentials.json

# Gmail トークンファイルのパス（自動生成、デフォルト: data/token.json）
GMAIL_TOKEN_PATH=data/token.json
```

**保存**: Ctrl+O → Enter → Ctrl+X

---

### 7. Google Sheets連携の設定（オプション）

Google Sheetsに会話記録を自動保存したい場合のみ設定してください。

#### 7.1 Google Cloud Consoleでの設定

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. **Google Sheets API** を有効化
4. **サービスアカウント** を作成
   - 役割: 「編集者」
   - キーのタイプ: JSON
5. JSONキーファイルをダウンロード

#### 7.2 認証ファイルの配置

```bash
# credentialsディレクトリを作成
mkdir -p credentials

# ダウンロードしたJSONファイルを配置
# 例: ローカルマシンからscpでコピー
# scp /path/to/your-service-account.json pi@raspberrypi.local:~/rzpy2025_10/credentials/google_service_account.json
```

#### 7.3 Googleスプレッドシートの準備

1. [Google Sheets](https://sheets.google.com/)で新しいスプレッドシートを作成
2. スプレッドシートのIDをコピー（URLの`/d/`と`/edit`の間の部分）
3. `.env`ファイルの`GOOGLE_SPREADSHEET_ID`に設定
4. **重要**: スプレッドシートをサービスアカウントのメールアドレスと共有（編集権限）
   - サービスアカウントのメール: `your-service-account@project-id.iam.gserviceaccount.com`

---

### 8. Gmail通知の設定（オプション）

異常検知時に家族へメール通知を送りたい場合のみ設定してください。

#### 8.1 Google Cloud Consoleでの設定

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス（Sheets用と同じプロジェクトでOK）
2. **Gmail API** を有効化
3. **OAuth 2.0 クライアントID** を作成
   - アプリケーションの種類: 「デスクトップアプリ」
   - クライアントIDをJSONでダウンロード

#### 8.2 認証ファイルの配置

```bash
# dataディレクトリを作成
mkdir -p data

# ダウンロードしたcredentials.jsonを配置
# 例: ローカルマシンからscpでコピー
# scp /path/to/credentials.json pi@raspberrypi.local:~/rzpy2025_10/data/credentials.json
```

#### 8.3 初回認証（デスクトップ環境が必要）

**重要**: 初回のみ、ブラウザでGoogleアカウントにログインして認証する必要があります。

```bash
# VNC経由でラズパイのデスクトップ環境に接続するか、
# ラズパイにモニター・キーボードを接続した状態で実行

cd ~/rzpy2025_10
source venv/bin/activate
python -c "from modules.email_notifier import EmailNotifier; EmailNotifier()"
```

ブラウザが開き、Googleアカウントでログインを求められます。許可すると`data/token.json`が自動生成されます。

---

## オーディオデバイスの設定

### 9. オーディオデバイスの確認

```bash
# 入力デバイス（マイク）の確認
arecord -l

# 出力デバイス（スピーカー）の確認
aplay -l
```

### 10. デフォルトオーディオデバイスの設定

`~/.asoundrc` ファイルを編集してデフォルトデバイスを設定：

```bash
nano ~/.asoundrc
```

以下の内容を記入（デバイス番号は`arecord -l`と`aplay -l`の結果に合わせて変更）：

```
pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"  # スピーカーのデバイス番号
    }
    capture.pcm {
        type plug
        slave.pcm "hw:1,0"  # マイクのデバイス番号
    }
}

ctl.!default {
    type hw
    card 0
}
```

### 11. オーディオのテスト

```bash
# マイクのテスト（5秒間録音）
arecord -d 5 -f cd test.wav

# 録音した音声を再生
aplay test.wav

# 動作確認できたら削除
rm test.wav
```

---

## 実行テスト

### 12. 動作確認

#### シンプル版（推奨：初回テスト用）

```bash
cd ~/rzpy2025_10
source venv/bin/activate
python simple_voice_chat.py
```

- マイクに向かって話しかけてください
- AIが音声で応答します
- 「終わり」「さようなら」で終了

#### フル機能版

```bash
cd ~/rzpy2025_10
source venv/bin/activate
python main.py
```

- リアルタイム音声会話 + 感情分析 + 記録 + 通知
- Google Sheets/Gmail設定済みの場合、自動で記録・通知されます

---

## 自動起動の設定（オプション）

### 13. systemdサービスの作成

毎日決まった時間に自動で会話を開始する場合は、systemdサービスとタイマーを設定します。

```bash
sudo nano /etc/systemd/system/care-conversation.service
```

以下の内容を記入：

```ini
[Unit]
Description=高齢者向け安否確認システム
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rzpy2025_10
Environment="PATH=/home/pi/rzpy2025_10/venv/bin"
ExecStart=/home/pi/rzpy2025_10/venv/bin/python /home/pi/rzpy2025_10/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 14. タイマーの設定（定時実行）

```bash
sudo nano /etc/systemd/system/care-conversation.timer
```

以下の内容を記入（10:00に実行する例）：

```ini
[Unit]
Description=安否確認システムタイマー（毎日10時）

[Timer]
OnCalendar=*-*-* 10:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 15. サービスの有効化

```bash
# サービスとタイマーをリロード
sudo systemctl daemon-reload

# タイマーを有効化
sudo systemctl enable care-conversation.timer

# タイマーを開始
sudo systemctl start care-conversation.timer

# タイマーの状態確認
sudo systemctl list-timers --all | grep care
```

---

## トラブルシューティング

### 音声が聞こえない
- `alsamixer`でボリュームを確認
- `~/.asoundrc`のデバイス番号を再確認
- `sudo reboot`で再起動

### マイクが認識されない
- `arecord -l`でデバイスが表示されるか確認
- USBマイクの場合は挿し直し
- `sudo reboot`で再起動

### OpenAI API接続エラー
- インターネット接続を確認
- `.env`ファイルの`OPENAI_API_KEY`を確認
- APIキーが正しいか、OpenAIのダッシュボードで確認

### Google Sheets書き込みエラー
- サービスアカウントのメールアドレスにスプレッドシートを共有しているか確認
- `credentials/google_service_account.json`が正しく配置されているか確認
- `.env`の`GOOGLE_SPREADSHEET_ID`が正しいか確認

### Gmail送信エラー
- `data/token.json`が存在するか確認
- 初回認証を完了しているか確認
- Gmail APIが有効化されているか確認（Google Cloud Console）

---

## 必要な設定項目一覧（コード修正不要）

### 必須設定

| 項目 | 設定場所 | 説明 |
|------|----------|------|
| OpenAI APIキー | `.env`の`OPENAI_API_KEY` | OpenAI APIへのアクセスキー |
| ユーザー名 | `.env`の`CARE_USER_NAME` | 利用者の名前 |
| オーディオデバイス | `~/.asoundrc` | マイク・スピーカーの設定 |

### オプション設定（Google Sheets連携）

| 項目 | 設定場所 | 説明 |
|------|----------|------|
| スプレッドシートID | `.env`の`GOOGLE_SPREADSHEET_ID` | 記録先のGoogleスプレッドシートID |
| サービスアカウント認証 | `credentials/google_service_account.json` | Google Sheets APIの認証ファイル |

### オプション設定（Gmail通知）

| 項目 | 設定場所 | 説明 |
|------|----------|------|
| Gmailアカウント | `.env`の`GMAIL_USER` | 送信元メールアドレス |
| 家族のメールアドレス | `.env`の`FAMILY_EMAILS` | 通知先メールアドレス（カンマ区切り） |
| OAuth2クライアント認証 | `data/credentials.json` | Gmail APIの認証ファイル |
| OAuth2トークン | `data/token.json` | Gmail APIのトークン（初回認証時に自動生成） |

### オプション設定（自動起動）

| 項目 | 設定場所 | 説明 |
|------|----------|------|
| systemdサービス | `/etc/systemd/system/care-conversation.service` | 実行サービスの定義 |
| systemdタイマー | `/etc/systemd/system/care-conversation.timer` | 定時実行の設定 |

---

## 参考情報

### ディレクトリ構成

```
/home/pi/rzpy2025_10/
├── .env                              # 環境変数設定（手動作成）
├── main.py                           # メインプログラム（フル機能）
├── simple_voice_chat.py              # シンプル版プログラム
├── requirements.txt                  # Python依存パッケージ
├── venv/                             # Python仮想環境
├── modules/                          # 各種モジュール
├── data/                             # データディレクトリ
│   ├── conversations.db              # 会話記録DB（自動生成）
│   ├── credentials.json              # Gmail OAuth2認証（手動配置）
│   └── token.json                    # Gmail トークン（自動生成）
├── credentials/                      # Google認証情報
│   └── google_service_account.json   # Sheets認証（手動配置）
├── logs/                             # ログファイル
│   └── app.log                       # アプリケーションログ（自動生成）
└── docs/                             # ドキュメント
    └── raspberry_pi_setup.md         # このファイル
```

### よく使うコマンド

```bash
# 仮想環境のアクティベート
source ~/rzpy2025_10/venv/bin/activate

# プログラムの実行
python main.py

# ログの確認
tail -f ~/rzpy2025_10/logs/app.log

# サービスの状態確認
sudo systemctl status care-conversation.service

# タイマーの確認
sudo systemctl list-timers --all | grep care

# サービスの停止
sudo systemctl stop care-conversation.service

# サービスの再起動
sudo systemctl restart care-conversation.service
```

---

## セキュリティ注意事項

1. **APIキーの保護**: `.env`ファイルは他人に見せないでください
2. **認証ファイルの管理**: `credentials/`と`data/`ディレクトリのJSONファイルは機密情報です
3. **スプレッドシートの共有**: 必要最小限の人とのみ共有してください
4. **定期的な更新**: `sudo apt update && sudo apt upgrade`でシステムを最新に保ってください

---

## サポート

問題が発生した場合は、以下を確認してください：
- `logs/app.log`のログファイル
- `systemctl status care-conversation.service`のサービス状態
- `.env`ファイルの設定内容

---

**最終更新**: 2025年10月3日






