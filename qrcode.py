from PIL import Image, ImageDraw
import copy

_LIGHT = 1
_DARK = 0

class CapacityOverflowException(Exception):
	def __init__(self, arg):
		self.arg = arg

	def __str__(self):
		return repr(self.arg)

def _matCp(src, dst, top, left):
	res = copy.deepcopy(dst)
	for x in range(len(src)):
		for y in range(len(src[0])):
			res[top+x][left+y] = src[x][y]
	return res

def _transpose(mat):
	res = [[mat[i][j] for i in range(len(mat))] for j in range(len(mat[0]))]
	return res

def _timSeq(len, vertical=False):
	res = [[i % 2 for i in range(len)]]
	if vertical:
		res = _transpose(res)
	return res

def _matAnd(mat1, mat2):
	res = [[_LIGHT for i in range(len(mat1[0]))] for j in range(len(mat1))]
	for i in range(len(mat1)):
		for j in range(len(mat1[0])):
			res[i][j] = int(mat1[i][j] == _LIGHT or mat2[i][j] == _LIGHT)
	return res

def _matXor(mat1, mat2):
	res = [[_LIGHT for i in range(len(mat1[0]))] for j in range(len(mat1))]
	for i in range(len(mat1)):
		for j in range(len(mat1[0])):
			res[i][j] = int(mat1[i][j] == mat2[i][j])
	return res

_finder = _matCp(_matCp([[_DARK for i in range(3)] for j in range(3)],
	[[_LIGHT for i in range(5)] for j in range(5)], 1, 1),
	[[_DARK for i in range(7)] for j in range(7)], 1, 1)
_align = _matCp(_matCp([[_DARK]],
	[[_LIGHT for i in range(3)] for j in range(3)], 1, 1),
	[[_DARK for i in range(5)] for j in range(5)], 1, 1)
_ver1 = [[_LIGHT for i in range(21)] for j in range(21)]
_ver1 = _matCp(_finder, _ver1, 0, 0)
_ver1 = _matCp(_finder, _ver1, 14, 0)
_ver1 = _matCp(_finder, _ver1, 0, 14)
_ver1 = _matCp(_timSeq(5), _ver1, 6, 8)
_ver1 = _matCp(_timSeq(5, vertical=True), _ver1, 8, 6)
_dataAreaMask = [[_DARK for i in range(21)] for j in range(21)]
_dataAreaMask = _matCp([[_LIGHT for i in range(9)] for j in range(9)],
	_dataAreaMask, 0, 0)
_dataAreaMask = _matCp([[_LIGHT for i in range(9)] for j in range(8)],
	_dataAreaMask, 13, 0)
_dataAreaMask = _matCp([[_LIGHT for i in range(8)] for j in range(9)],
	_dataAreaMask, 0, 13)
_dataAreaMask = _matCp([[_LIGHT for i in range(4)]], _dataAreaMask, 6, 9)
_dataAreaMask = _matCp([[_LIGHT] for i in range(4)], _dataAreaMask, 9, 6)
_dataMasks = []
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if (i+j)%2==0 else _LIGHT for i in range(21)] for j in range(21)]))
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if j%2==0 else _LIGHT for i in range(21)] for j in range(21)]))
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if i%3==0 else _LIGHT for i in range(21)] for j in range(21)]))
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if (i+j)%3==0 else _LIGHT for i in range(21)] for j in range(21)]))
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if (j/2 + i/3)%2==0 else _LIGHT for i in range(21)] for j in range(21)]))
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if (i*j)%2+(i*j)%3==0 else _LIGHT for i in range(21)] for j in range(21)]))
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if ((i*j)%2+(i*j)%3)%2==0 else _LIGHT for i in range(21)] for j in range(21)]))
_dataMasks.append(_matAnd(_dataAreaMask, [[_DARK if ((i+j)%2+(i*j)%3)%2==0 else _LIGHT for i in range(21)] for j in range(21)]))

def _gfpMul(x, y, prim=0x11d, field_charac_full=256, carryless=True):
	r = 0
	while y:
		if y & 1:
			r = r ^ x if carryless else r + x
		y = y >> 1
		x = x << 1
		if prim > 0 and x & field_charac_full:
			x = x ^ prim
	return r

_gfExp = [0] * 512
_gfLog = [0] * 256
_gfPrim = 0x11d

_x = 1

for i in range(255):
	_gfExp[i] = _x
	_gfLog[_x] = i
	_x = _gfpMul(_x, 2)

for i in range(255, 512):
	_gfExp[i] = _gfExp[i-255]

def _gfPow(x, pow):
	return _gfExp[(_gfLog[x] * pow) % 255]

def _gfMul(x, y):
	if x == 0 or y == 0:
		return 0
	return _gfExp[_gfLog[x] + _gfLog[y]]

def _gfPolyMul(p, q):
	r = [0] * (len(p) + len(q) - 1)
	for j in range(len(q)):
		for i in range(len(p)):
			r[i+j] ^= _gfMul(p[i], q[j])
	return r

def _gfPolyDiv(dividend, divisor):
	res = list(dividend)
	for i in range(len(dividend) - len(divisor) + 1):
		coef = res[i]
		if coef != 0:
			for j in range(1, len(divisor)):
				if divisor[j] != 0:
					res[i+j] ^= _gfMul(divisor[j], coef)
	sep = -(len(divisor) - 1)
	return res[:sep], res[sep:]

def _rsGenPoly(nsym):
	g = [1]
	for i in range(nsym):
		g = _gfPolyMul(g, [1, _gfPow(2, i)])
	return g

def _rsEncode(bitstring, nsym):
	gen = _rsGenPoly(nsym)
	res = [0] * (len(bitstring) + len(gen) - 1)
	res[:len(bitstring)] = bitstring
	for i in range(len(bitstring)):
		coef = res[i]
		if coef != 0:
			for j in range(1, len(gen)):
				res[i+j] ^= _gfMul(gen[j], coef)
	res[:len(bitstring)] = bitstring
	return res

def _fmtEncode(fmt):
	g = 0x537
	code = fmt << 10
	for i in range(4,-1,-1):
		if code & (1 << (i+10)):
			code ^= g << i
	return ((fmt << 10) ^ code) ^ 0b101010000010010

def _encode(data):
	if len(data) > 17:
		raise CapacityOverflowException('Error: Version 1 QR code encodes no more than 17 characters.')
	bitstring = '0100'
	bitstring += '{:08b}'.format(len(data))
	for c in data:
		bitstring += '{:08b}'.format(ord(c.encode('iso-8859-1')))
	bitstring += '0000'
	res = list()
	while bitstring:
		res.append(int(bitstring[:8], 2))
		bitstring = bitstring[8:]
	while len(res) < 19:
		res.append(int('11101100', 2))
		res.append(int('00010001', 2))
	res = res[:19]
	return _rsEncode(res, 7)

def _fillByte(byte, downwards=False):
	bytestr = '{:08b}'.format(byte)
	res = [[0, 0], [0, 0], [0, 0], [0, 0]]
	for i in range(8):
		res[i/2][i%2] = not int(bytestr[7-i])
	if downwards:
		res = res[::-1]
	return res

def _fillData(bitstream):
	res = copy.deepcopy(_ver1)
	for i in range(15):
		res = _matCp(_fillByte(bitstream[i], (i/3)%2!=0),
			res,
			21-4*((i%3-1)*(-1)**((i/3)%2)+2),
			21-2*(i/3+1))
	tmp = _fillByte(bitstream[15])
	res = _matCp(tmp[2:], res, 7, 11)
	res = _matCp(tmp[:2], res, 4, 11)
	tmp = _fillByte(bitstream[16])
	res = _matCp(tmp, res, 0, 11)
	tmp = _fillByte(bitstream[17], True)
	res = _matCp(tmp, res, 0, 9)
	tmp = _fillByte(bitstream[18], True)
	res = _matCp(tmp[:2], res, 4, 9)
	res = _matCp(tmp[2:], res, 7, 9)
	for i in range(3):
		res = _matCp(_fillByte(bitstream[19+i], True),
			res, 9+4*i, 9)
	tmp = _fillByte(bitstream[22])
	res = _matCp(tmp, res, 9, 7)
	for i in range(3):
		res = _matCp(_fillByte(bitstream[23+i], i%2==0),
			res, 9, 4-2*i)
	return res

def _fillInfo(arg):
	mat, mask = arg
	fmt = _fmtEncode(int('01'+'{:03b}'.format(mask), 2))
	fmtarr = [[not int(c)] for c in '{:015b}'.format(fmt)]
	mat = _matCp(_transpose(fmtarr[7:]), mat, 8, 13)
	mat = _matCp(fmtarr[9:][::-1], mat, 0, 8)
	mat = _matCp(fmtarr[7:9][::-1], mat, 7, 8)
	mat = _matCp(fmtarr[:7][::-1], mat, 14, 8)
	mat = _matCp(_transpose(fmtarr[:6]), mat, 8, 0)
	mat = _matCp([fmtarr[6]], mat, 8, 7)
	return mat

def _penalty(mat):
	n1 = n2 = n3 = n4 = 0
	for x in range(len(mat)):
		count = 1
		adj = False
		for y in range(1, len(mat)):
			if mat[x][y] == mat[x][y-1]:
				count += 1
			else:
				count = 1
				adj = False
			if count >= 5:
				if not adj:
					adj = True
					n1 += 3
				else:
					n1 += 1
	for y in range(len(mat)):
		count = 1
		adj = False
		for x in range(1, len(mat)):
			if mat[x][y] == mat[x-1][y]:
				count += 1
			else:
				count = 1
				adj = False
			if count >= 5:
				if not adj:
					adj = True
					n1 += 3
				else:
					n1 += 1
	m = n = 1
	for x in range(1, len(mat)):
		for y in range(1, len(mat)):
			if mat[x][y] == mat[x-1][y] and mat[x][y] == mat[x][y-1] and mat[x][y] == mat[x-1][y-1]:
				if mat[x][y] == mat[x-1][y]:
					m += 1
				if mat[x][y] == mat[x][y-1]:
					n += 1
			else:
				n2 += 3 * (m-1) * (n-1)
				m = n = 1
	count = 0
	for row in mat:
		rowstr = ''.join(str(e) for e in row)
		occurrences = []
		begin = 0
		while rowstr.find('0100010', begin) != -1:
			begin = rowstr.find('0100010', begin) + 7
			occurrences.append(begin)
		for begin in occurrences:
			if rowstr.count('00000100010', begin-4) != 0 or rowstr.count('01000100000', begin) != 0:
				count += 1
	transposedMat = _transpose(mat)
	for row in transposedMat:
		rowstr = ''.join(str(e) for e in row)
		occurrences = []
		begin = 0
		while rowstr.find('0100010', begin) != -1:
			begin = rowstr.find('0100010', begin) + 7
			occurrences.append(begin)
		for begin in occurrences:
			if rowstr.count('00000100010', begin-4) != 0 or rowstr.count('01000100000', begin) != 0:
				count += 1
	n3 += 40 * count
	dark = sum(row.count(_DARK) for row in mat)
	percent = int((float(dark) / float(len(mat)**2)) * 100)
	pre = percent - percent % 5
	nex = percent + 5 - percent % 5
	n4 = min(abs(pre-50)/5, abs(nex-50)/5) * 10
	return n1 + n2 + n3 + n4

def _mask(mat):
	maskeds = [_matXor(mat, dataMask) for dataMask in _dataMasks]
	penalty = [0] * 8
	for i, masked in enumerate(maskeds):
		penalty[i] = _penalty(masked)
	index = penalty.index(min(penalty))
	return maskeds[index], index

def _genBitmap(bitstream):
	return _fillInfo(_mask(_fillData(bitstream)))

def _genImage(bitmap, width, filename):
	img = Image.new('1', (width, width), 'white')
	drw = ImageDraw.Draw(img)
	pwidth = width / len(bitmap)
	for x in range(width):
		normalx = x / pwidth
		for y in range(width):
			normaly = y / pwidth
			if normalx < len(bitmap) and normaly < len(bitmap):
				drw.point((y, x), fill=bitmap[normalx][normaly])
	img.save(filename)

def qrcode(data, width=210, filename='qrcode.jpg'):
	try:
		_genImage(_genBitmap(_encode(data)), width, filename)
	except Exception, e:
		print e
		raise e