# Apocalipsis — imágenes de las escenas

Genera cada imagen en **16:9 y a la máxima resolución** (Higgsfield, Leonardo, Ideogram,
Midjourney, Bing Image Creator o Canva). Guárdala con el **nombre exacto** de la tabla
(`.jpg`, `.png` o `.webp`) y súbela a `pelicula_apocalipsis/recursos/originales/`.

Después:

```bash
python3 preparar_imagenes.py   # amplía, restaura rostros (GFPGAN) y calcula profundidad
python3 generar_pelicula.py    # renderiza apocalipsis.mp4
```

| Archivo | Prompt |
|---|---|
| `01_patmos` | Cinematic film still, biblical epic movie, close-up of the elderly apostle John with a long white beard writing on a parchment scroll inside a rocky cave on the island of Patmos, warm candlelight illuminating his wrinkled face, eyes looking up in awe, the sea visible through the cave opening at dusk, shallow depth of field, photorealistic detailed skin, 35mm anamorphic film look |
| `02_sellos` | Cinematic film still, biblical epic movie, close-up of an ancient parchment scroll bound with seven red wax seals resting on a golden altar, divine golden light beam from above, floating dust particles, deep dark background, macro shot, photorealistic, 35mm film look |
| `03_caballo_blanco` | Cinematic film still, biblical apocalypse epic, a regal rider on a powerful white horse charging toward the camera, the rider holds a bow and wears a golden crown and a flowing white cloak, dramatic storm clouds, low angle hero shot, strong backlight rim light, dust kicked up, photorealistic face, 35mm anamorphic film look |
| `04_caballo_rojo` | Cinematic film still, biblical apocalypse epic, a fierce armored warrior riding a blood red horse, raising a great sword above his head, battlefield with fire and black smoke behind him, crimson and orange firelight on his face, low angle, photorealistic intense face, 35mm anamorphic film look |
| `05_caballo_negro` | Cinematic film still, biblical apocalypse epic, a gaunt stern rider in dark robes on a black horse holding up a pair of bronze balance scales, barren cracked famine wasteland, cold desaturated overcast light, dark heavy clouds, medium shot, photorealistic face, 35mm anamorphic film look |
| `06_caballo_amarillo` | Cinematic film still, dark fantasy apocalypse epic, a hooded rider called Death with a pale gaunt face riding a sickly pale grey-green horse through thick mist, shadowy figures following behind, eerie green-grey moonlight, desolate wasteland, low angle, 35mm anamorphic film look |
| `07_cuatro_jinetes` | Cinematic film still, apocalypse epic, the four horsemen riding side by side toward the camera across a burning plain, one white horse, one red horse, one black horse and one pale horse, apocalyptic sky glowing with fire, epic wide shot, dust and embers in the air, dramatic lighting, 35mm anamorphic film look |
| `08_sexto_sello` | Cinematic film still, apocalypse epic, a great earthquake splitting the land, the sun turned black and a huge blood red moon in the sky, burning stars falling like meteors, tiny people fleeing toward the mountains, epic wide shot, red and black color palette, 35mm anamorphic film look |
| `09_bestia_mar` | Cinematic film still, dark fantasy epic, a colossal monster rising out of a stormy sea, it has seven heads and ten horns with ten golden crowns on the horns, a spotted body like a leopard, feet like a bear, mouths like a lion, huge dark waves crashing, lightning in the sky, epic low angle, photorealistic creature, 35mm anamorphic film look |
| `10_bestia_cabeza` | Cinematic film still, dark fantasy epic, close-up of a monstrous lion-like head with long horns and a golden crown, roaring with open jaws, one of seven heads of a sea beast, seawater dripping, lightning illuminating wet fur and scales, dark stormy background, photorealistic creature, 35mm film look |
| `11_bestia_tierra` | Cinematic film still, dark fantasy epic, a monstrous beast rising from cracked volcanic earth, it has two small horns like a lamb but a dragon-like reptilian face with glowing red eyes, calling fire down from the sky in front of a terrified crowd, fire raining from dark clouds, orange volcanic light, low angle, photorealistic creature, 35mm anamorphic film look |
| `12_marca` | Cinematic film still, dark epic, close-up of an ancient black stone tablet engraved with the number 666 glowing red hot like molten metal, embers and smoke rising, ominous darkness, dramatic side light, photorealistic, 35mm film look |
| `13_fiel_verdadero` | Cinematic film still, biblical epic, a majestic rider on a white horse descending from an opened heaven, eyes like flames of fire, many golden crowns on his head, white robe, armies of heaven on white horses behind him in the clouds, radiant golden light rays, epic low angle, photorealistic face, 35mm anamorphic film look |
| `14_nueva_jerusalen` | Cinematic film still, biblical epic, the holy city New Jerusalem made of gold and crystal descending from heaven through the clouds, twelve gates of pearl, radiant divine light, a new earth below with rivers and green valleys at dawn, epic wide shot, photorealistic, 35mm anamorphic film look |

## Guion (narración)

Cada escena ya tiene su narración, subtítulos, rótulo de capítulo, movimiento de cámara 2.5D,
efectos y música definidos en `generar_pelicula.py` (lista `ESCENAS`). La película termina con
la leyenda de Apocalipsis 22:12-13 y el Alfa y la Omega, sin créditos de autor.
