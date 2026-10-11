import io
import os
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path
from flask import Flask, request, render_template, send_file, jsonify

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1 GiB compressed upload

DIM = {'overworld': None, 'nether': 1, 'end': 2}
# Minecraft Bedrock LevelChunkTag values (include older/modern chunk record tags).
CHUNK_TAGS = set(range(0x2b, 0x40)) | {0x76, 0x77}
MAX_CHUNKS = 50000


def safe_unzip(upload, target):
    with zipfile.ZipFile(upload) as z:
        infos = z.infolist()
        if len(infos) > 100000 or sum(i.file_size for i in infos) > 4 * 1024**3:
            raise ValueError('ZIP grande demais para o limite de segurança (4 GB descompactados).')
        for info in infos:
            name = info.filename.replace('\\', '/')
            path = Path(name)
            if path.is_absolute() or '..' in path.parts or ':' in name:
                raise ValueError('Arquivo ZIP contém um caminho inseguro.')
            if info.is_dir():
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Links simbólicos não são permitidos.')
            dest = (target / path).resolve()
            if not dest.is_relative_to(target.resolve()):
                raise ValueError('Caminho inseguro no ZIP.')
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, dest.open('wb') as dst:
                shutil.copyfileobj(src, dst)


def find_world(root):
    candidates = [p.parent for p in root.rglob('level.dat') if (p.parent / 'db' / 'CURRENT').is_file()]
    if len(candidates) != 1:
        raise ValueError('O ZIP precisa conter exatamente um mundo Bedrock com level.dat e db/CURRENT.')
    return candidates[0]


def wanted_key(key, cx0, cx1, cz0, cz1, dim):
    # Standard chunk keys: <chunkX:int32><chunkZ:int32>[<dimension:int32>]<tag><subchunk?>
    if len(key) in (9, 10, 13, 14):
        x, z = struct.unpack_from('<ii', key)
        if not (cx0 <= x <= cx1 and cz0 <= z <= cz1):
            return False
        if dim is None:
            return len(key) in (9, 10) and key[8] in CHUNK_TAGS
        return len(key) in (13, 14) and struct.unpack_from('<i', key, 8)[0] == dim and key[12] in CHUNK_TAGS
    # digp indexes enumerate actor IDs per chunk; current Bedrock entity storage.
    if key.startswith(b'digp') and len(key) in (12, 16):
        x, z = struct.unpack_from('<ii', key, 4)
        if not (cx0 <= x <= cx1 and cz0 <= z <= cz1):
            return False
        if dim is None:
            return len(key) == 12
        return len(key) == 16 and struct.unpack_from('<i', key, 12)[0] == dim
    return False


def open_leveldb(path):
    try:
        from leveldb import LevelDB
    except ImportError:
        try:
            from amulet.leveldb import LevelDB
        except ImportError as exc:
            raise RuntimeError('Falta instalar amulet-leveldb. Rode: pip install -r requirements.txt') from exc
    return LevelDB(str(path))


def modify_world(db_path, coords, dimension):
    db = open_leveldb(db_path)
    try:
        # Collect first; do not delete keys during iteration.
        keys = [key for key, _ in db.iterate() if wanted_key(key, *coords, DIM[dimension])]
        for key in keys:
            db.delete(key)
        return len(keys)
    finally:
        close = getattr(db, 'close', None)
        if close:
            close()
        del db


@app.get('/health')
def health():
    return jsonify(ok=True)


@app.get('/')
def home():
    return render_template('index.html')


@app.post('/reset')
def reset():
    try:
        uploaded = request.files.get('world')
        if uploaded is None or not uploaded.filename.lower().endswith(('.zip', '.mcworld')):
            return jsonify(error='Envie um mundo .zip ou .mcworld.'), 400
        dim = request.form.get('dimension', '')
        if dim not in DIM:
            return jsonify(error='Dimensão inválida.'), 400
        x1, z1, x2, z2 = [int(request.form[k]) for k in ('x1', 'z1', 'x2', 'z2')]
        a, b = sorted((x1 // 16, x2 // 16))
        c, d = sorted((z1 // 16, z2 // 16))
        count = (b - a + 1) * (d - c + 1)
        if count > MAX_CHUNKS:
            return jsonify(error=f'Seleção grande demais: {count} chunks. Limite: {MAX_CHUNKS}.'), 400
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'input'
            root.mkdir()
            safe_unzip(uploaded.stream, root)
            world = find_world(root)
            deleted = modify_world(world / 'db', (a, b, c, d), dim)
            output = io.BytesIO()
            # Bundle world at the archive root so MC can import as .mcworld.
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as z:
                for p in world.rglob('*'):
                    if p.is_file() and p.name not in ('LOCK',):
                        z.write(p, p.relative_to(world).as_posix())
            output.seek(0)
            res = send_file(output, as_attachment=True, download_name='mundo_chunks_resetadas.mcworld', mimetype='application/octet-stream')
            res.headers['X-Chunks-Selected'] = str(count)
            res.headers['X-Records-Deleted'] = str(deleted)
            return res
    except (ValueError, KeyError, zipfile.BadZipFile) as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        app.logger.exception('Falha no processamento')
        return jsonify(error=f'Falha ao editar o banco Bedrock: {e}'), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050, debug=False)
