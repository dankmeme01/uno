from pathlib import Path

fp = open(Path(__file__).parent.parent / "cards.png.sheet", 'w')

beginx = x = 20
beginy = y = 18

width = 188
height = 282

def get_name(row, col):
    row += 1
    match row:
        case 1:
            color = "red" if col < 9 else "wild"
            type_ = (str(col + 1) if col < 9 else 'color')
        case 2:
            color = "yellow" if col < 9 else "wild"
            type_ = (str(col + 1) if col < 9 else 'color')
        case 3:
            color = "blue" if col < 9 else "wild"
            type_ = (str(col + 1) if col < 9 else '+4')
        case 4:
            color = "green" if col < 9 else "wild"
            type_ = (str(col + 1) if col < 9 else '+4')
        case 5:
            color = ["red", "yellow", "blue", "green"][col % 4]
            type_ = ["block", "+2", "reverse"][col // 4]
        case 6:
            if col < 2:
                color = "blue" if col == 0 else "green"
                type_ = ["reverse", "reverse"][col % 2]
                # will keep this lmao copilot is op lol
            elif col < 6:
                color = ["red", "yellow", "blue", "green"][(col - 2) % 4]
                type_ = "+4"
            elif col < 10:
                color = ["red", "yellow", "blue", "green"][(col - 6) % 4]
                type_ = "color"

    return f'{color}_{type_}'

used = []

for row in range(6):
    for col in range(10):
        if col == 0:
            x = beginx
        else:
            x += width
        
        name = get_name(row, col)
        if name not in used: # same sprite can repeat twice, eliminate that.
            used.append(name)
            fp.write(f'{name} {x} {y} {width} {height}\n')
    y += height

fp.close()