from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import uuid
import time
import json
from datetime import datetime, timedelta
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech.transcription import ConversationTranscriber
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # フロントエンドからのCORSリクエストを許可

# 設定
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'mp3', 'm4a', 'wav', 'flac', 'ogg', 'webm'}
UPLOAD_FOLDER = 'temp_uploads'

# アップロードフォルダの作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class SpeechTranscriptionService:
    def __init__(self):
        # 環境変数からAzure認証情報を取得
        self.speech_key = os.environ.get('AZURE_SPEECH_KEY')
        self.speech_region = os.environ.get('AZURE_SPEECH_REGION')
        
        if not self.speech_key or not self.speech_region:
            raise ValueError("環境変数 AZURE_SPEECH_KEY と AZURE_SPEECH_REGION を設定してください")
        
        logger.info("Azure Speech Service initialized")
    
    def create_speech_config(self, language='ja-JP'):
        """音声認識の設定を作成"""
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, 
            region=self.speech_region
        )
        speech_config.speech_recognition_language = language
        
        # 話者認識を有効にする
        speech_config.request_word_level_timestamps()
        speech_config.enable_dictation()
        
        return speech_config
    
    def convert_audio_format(self, input_file_path, output_file_path):
        """音声ファイルをWAV形式に変換（必要に応じて）"""
        try:
            import pydub
            
            # ファイル拡張子から形式を判定
            if input_file_path.lower().endswith('.mp3'):
                audio = pydub.AudioSegment.from_mp3(input_file_path)
            elif input_file_path.lower().endswith('.m4a'):
                audio = pydub.AudioSegment.from_file(input_file_path, format="m4a")
            elif input_file_path.lower().endswith('.flac'):
                audio = pydub.AudioSegment.from_file(input_file_path, format="flac")
            elif input_file_path.lower().endswith('.ogg'):
                audio = pydub.AudioSegment.from_file(input_file_path, format="ogg")
            else:
                # すでにWAVまたは他の対応形式
                return input_file_path
            
            # WAV形式で保存（16kHz, モノラル）
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(output_file_path, format="wav")
            
            logger.info(f"Audio converted to WAV: {output_file_path}")
            return output_file_path
            
        except ImportError:
            logger.warning("pydub not installed. Skipping audio conversion.")
            return input_file_path
        except Exception as e:
            logger.error(f"Audio conversion failed: {str(e)}")
            return input_file_path

    def transcribe_with_speaker_recognition(self, audio_file_path, language='ja-JP', max_speakers=6):
        """話者認識付きで音声をテキスト化"""
        try:
            # 音声設定を作成
            speech_config = self.create_speech_config(language)
            
            # WAV形式に変換
            wav_file_path = audio_file_path.replace(os.path.splitext(audio_file_path)[1], '_converted.wav')
            converted_path = self.convert_audio_format(audio_file_path, wav_file_path)
            
            # 音声ファイルの設定
            audio_config = speechsdk.audio.AudioConfig(filename=converted_path)
            
            # 会話転写器を作成
            conversation_transcriber = speechsdk.transcription.ConversationTranscriber(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # 結果を格納する変数
            transcription_results = []
            transcription_done = False
            
            def handle_final_result(evt):
                """最終的な認識結果を処理"""
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    # 話者IDと認識テキストを取得
                    speaker_id = evt.result.speaker_id if hasattr(evt.result, 'speaker_id') else "Unknown"
                    
                    # タイムスタンプを計算
                    offset_ticks = evt.result.offset
                    duration_ticks = evt.result.duration
                    
                    start_time = self.ticks_to_time_string(offset_ticks)
                    end_time = self.ticks_to_time_string(offset_ticks + duration_ticks)
                    
                    result = {
                        'speaker': f'話者{speaker_id}' if speaker_id != "Unknown" else "話者1",
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': evt.result.text,
                        'confidence': getattr(evt.result, 'confidence', 0.9)
                    }
                    
                    transcription_results.append(result)
                    logger.info(f"Transcribed: {result}")
            
            def handle_canceled(evt):
                """キャンセル時の処理"""
                nonlocal transcription_done
                logger.error(f"Transcription canceled: {evt.result.cancellation_details.reason}")
                if evt.result.cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {evt.result.cancellation_details.error_details}")
                transcription_done = True
            
            def handle_session_stopped(evt):
                """セッション終了時の処理"""
                nonlocal transcription_done
                logger.info("Transcription session stopped")
                transcription_done = True
            
            # イベントハンドラーを接続
            conversation_transcriber.transcribed.connect(handle_final_result)
            conversation_transcriber.canceled.connect(handle_canceled)
            conversation_transcriber.session_stopped.connect(handle_session_stopped)
            
            # 転写を開始
            logger.info("Starting conversation transcription...")
            conversation_transcriber.start_transcribing_async().get()
            
            # 転写完了まで待機
            timeout = 300  # 5分タイムアウト
            start_wait_time = time.time()
            
            while not transcription_done and (time.time() - start_wait_time) < timeout:
                time.sleep(0.5)
            
            # 転写を停止
            conversation_transcriber.stop_transcribing_async().get()
            
            # 変換したファイルを削除
            if converted_path != audio_file_path and os.path.exists(converted_path):
                os.remove(converted_path)
            
            if not transcription_results:
                # 話者認識が失敗した場合、通常の音声認識にフォールバック
                logger.info("Falling back to regular speech recognition...")
                return self.fallback_transcription(audio_file_path, language)
            
            # 結果をタイムスタンプでソート
            transcription_results.sort(key=lambda x: x['start_time'])
            
            return {
                'success': True,
                'results': transcription_results,
                'total_segments': len(transcription_results)
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def fallback_transcription(self, audio_file_path, language='ja-JP'):
        """通常の音声認識（話者認識なし）"""
        try:
            speech_config = self.create_speech_config(language)
            
            # WAV形式に変換
            wav_file_path = audio_file_path.replace(os.path.splitext(audio_file_path)[1], '_fallback.wav')
            converted_path = self.convert_audio_format(audio_file_path, wav_file_path)
            
            audio_config = speechsdk.audio.AudioConfig(filename=converted_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # 連続認識の結果を格納
            results = []
            
            def handle_result(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    offset_ticks = evt.result.offset
                    duration_ticks = evt.result.duration
                    
                    start_time = self.ticks_to_time_string(offset_ticks)
                    end_time = self.ticks_to_time_string(offset_ticks + duration_ticks)
                    
                    result = {
                        'speaker': '話者1',
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': evt.result.text,
                        'confidence': 0.8
                    }
                    results.append(result)
            
            speech_recognizer.recognized.connect(handle_result)
            
            # 連続認識を開始
            speech_recognizer.start_continuous_recognition_async().get()
            
            # 音声ファイルの処理完了まで待機
            time.sleep(10)  # 実際の実装では音声の長さに応じて調整
            
            speech_recognizer.stop_continuous_recognition_async().get()
            
            # 変換したファイルを削除
            if converted_path != audio_file_path and os.path.exists(converted_path):
                os.remove(converted_path)
            
            return {
                'success': True,
                'results': results,
                'total_segments': len(results),
                'note': '話者認識は使用されませんでした'
            }
            
        except Exception as e:
            logger.error(f"Fallback transcription error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def ticks_to_time_string(self, ticks):
        """ticksを時間文字列に変換"""
        # 1 tick = 100 nanoseconds
        seconds = ticks / 10000000
        time_obj = datetime.utcfromtimestamp(seconds)
        return time_obj.strftime('%H:%M:%S')

def allowed_file(filename):
    """ファイル拡張子をチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'OK',
        'message': 'Speech Recognition API is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """音声ファイルを受け取ってテキスト化"""
    try:
        # ファイルの存在確認
        if 'audio_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'audio_fileが見つかりません'
            }), 400
        
        file = request.files['audio_file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'ファイルが選択されていません'
            }), 400
        
        # ファイル形式チェック
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'対応していないファイル形式です。対応形式: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # ファイルサイズチェック
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'ファイルサイズが大きすぎます。最大: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400
        
        # リクエストパラメータの取得
        language = request.form.get('language', 'ja-JP')
        max_speakers = int(request.form.get('max_speakers', 6))
        
        # 一時ファイルに保存
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(file_path)
        logger.info(f"File saved: {file_path}")
        
        # 音声認識サービスの初期化
        service = SpeechTranscriptionService()
        
        # 音声をテキスト化
        logger.info(f"Starting transcription for file: {filename}")
        result = service.transcribe_with_speaker_recognition(
            file_path, 
            language=language, 
            max_speakers=max_speakers
        )
        
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)
        
        logger.info(f"Transcription completed. Success: {result['success']}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Transcription API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'サーバーエラー: {str(e)}'
        }), 500

@app.route('/supported-languages', methods=['GET'])
def get_supported_languages():
    """対応言語の一覧を返す"""
    languages = {
        'ja-JP': '日本語',
        'en-US': '英語（アメリカ）',
        'en-GB': '英語（イギリス）',
        'zh-CN': '中国語（簡体字）',
        'ko-KR': '韓国語',
        'es-ES': 'スペイン語',
        'fr-FR': 'フランス語',
        'de-DE': 'ドイツ語',
        'it-IT': 'イタリア語',
        'pt-BR': 'ポルトガル語（ブラジル）'
    }
    
    return jsonify({
        'success': True,
        'languages': languages
    })

@app.errorhandler(413)
def too_large(e):
    """ファイルサイズエラーハンドラー"""
    return jsonify({
        'success': False,
        'error': 'ファイルサイズが大きすぎます'
    }), 413

if __name__ == '__main__':
    # 本番環境では適切な設定を行う
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    app.run(debug=True, host='0.0.0.0', port=5000)