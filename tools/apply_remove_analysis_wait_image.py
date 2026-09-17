from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')

text = text.replace("  const TEMP_WAIT_IMAGE='https://i.imgur.com/CduyK.jpeg';\n\n", "")

image_block = """    const img=document.createElement('img');
    img.src=TEMP_WAIT_IMAGE;
    img.alt='Очікування завершення аналізу TLOG';
    img.referrerPolicy='no-referrer';
    Object.assign(img.style,{
      display:'block',
      width:'100%',
      maxHeight:'68vh',
      objectFit:'contain',
      borderRadius:'10px',
      background:'#090d12'
    });

"""

if image_block not in text:
    if "card.append(title,subtitle);" in text and "TEMP_WAIT_IMAGE" not in text:
        raise SystemExit(0)
    raise SystemExit('analysis wait image block not found')

text = text.replace(image_block, '', 1)
text = text.replace('    card.append(img,title,subtitle);', '    card.append(title,subtitle);', 1)
path.write_text(text, encoding='utf-8')
