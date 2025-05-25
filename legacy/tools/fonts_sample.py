from PIL import Image, ImageDraw, ImageFont

image = Image.new("RGB", (800, 600), color="white")
draw = ImageDraw.Draw(image)

# Load a custom font
font = ImageFont.truetype("fonts/damion-font/Damion-8gnD.ttf", size=50)

text = "Hello, World!"
position = (250, 250)  # (x, y) coordinates
draw.text(position, text, font=font, fill="black")
image.show()
