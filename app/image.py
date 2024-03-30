from PIL import Image, ImageDraw, ImageFont

# Create a new image with a white background
image = Image.new('RGB', (400, 200), 'white')

# Initialize the drawing context
draw = ImageDraw.Draw(image)

# Define the text and font
text = "QUESTION\nWhich of the following is a cloud cost optimization strategy for storage?\nANSWER\nCold Storage"
font = ImageFont.truetype('arial.ttf', 20)

# Add the text to the image
draw.text((10, 10), text, fill='black', font=font)

# Save the image to a file
image.save('generated_image.png')