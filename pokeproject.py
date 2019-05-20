import os

#Työkansio: se kansio, jossa datasetit ovat, tulee tähän
os.chdir('C:\\Users\Tattimatonen\Pokeproject')

#Ladataan datasettejä
import pandas as pd

locationCols = ['pokemonId', 'city']
cityCols = ['name', 'country']
pokemonCols = ['pokedex_number', 'name', 'type1', 'type2', 'classfication', 'percentage_male', 'height_m', 'weight_kg', 'hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']
pogoCols = ['Pokemon No.', 'Max CP', 'Max HP', 'Image URL']

sijainnit = pd.read_csv('predictEmAll.csv', skipinitialspace=True, usecols=locationCols)
kaupungit = pd.read_csv('worldCities.csv', skipinitialspace=True, usecols=cityCols)
pokemon = pd.read_csv('pokeStats.csv', skipinitialspace=True, usecols=pokemonCols)
pogo = pd.read_csv('pogoStats.csv', skipinitialspace=True, usecols=pogoCols)

#Manipuloidaan pokemondataa
pokemonData = pokemon.merge(pogo, left_on = 'pokedex_number', right_on = 'Pokemon No.')
pokemonData = pokemonData.drop('Pokemon No.', axis=1)
pokemonData = pokemonData.rename(columns={'pokedex_number':'pokemonId'})

#Päätellään pokemonien maat niiden kaupungeista
sijainnit['city'] = sijainnit['city'].str.replace('_', ' ')
sijainnit['city'] = sijainnit['city'].str.lower()

kaupungit['name'] = kaupungit['name'].str.lower()

#HUOM: koska maiden nimessä toistuvuutta, n. <5% virheellisyys datassa.
#Olisimme käyttäneet reverse geocachingia, mutta maksaa rahaa, että sen
#Olisimme käyttäneet reverse geocachingia, mutta maksaa rahaa, että sen
#saa tehtyä n. 300 000 riville koordinaatteja. Harjoitusmielessä tämä
#lienee riittävää.
merged = sijainnit.merge(kaupungit, left_on = 'city', right_on = 'name')
merged = merged.drop(['city', 'name'], axis=1)

#Piirretään karttaa
import geopandas as gpd

shapefile = 'ne_110m_admin_0_countries.shp'

#Luetaan kartan muodot GeoPandasilla
kartta = gpd.read_file(shapefile)[['ADMIN','ADM0_A3', 'geometry']]

#Uudelleennimetään
kartta.columns = ['country', 'country_code', 'geometry']

#Poistetaan etelämanner
kartta = kartta.drop(kartta.index[159])

pokemonMaatCount = merged.groupby('country').count()
pokemonMaatCount.rename(columns={'pokemonId':'count'}, inplace=True)

#Mergen ongelmamaat: Tsekki, USA, Hong Kong, Singapore
#Korjataan ongelmamaat ennen mergeä (ei infoa Hong Kongista eikä Singaporesta, varmaankin koska ennemmin territorioita kuin maita?)
kartta = kartta.replace('Czechia', 'Czech Republic')
kartta = kartta.replace('United States of America', 'United States')

pokemonKartta = kartta.merge(pokemonMaatCount, left_on = 'country', right_on = 'country', how = 'left')
pokemonKartta.fillna('No Data', inplace = True)

#Pokemondatan manipulointia, etsitään montako kutakin pokemonia on per maa
pokemonLocationData = pokemonData.merge(merged, left_on = 'pokemonId', right_on = 'pokemonId')
pokemonNameData = pokemonData.drop(['attack', 'defense', 'sp_attack', 'sp_defense', 'hp', 'speed', 'percentage_male', 'height_m', 'weight_kg', 'Image URL', 'classfication'], axis=1)

#Isot alkukirjaimet ovat nättejä
pokemonNameData['type1'] = pokemonNameData['type1'].str.capitalize()
pokemonNameData['type2'] = pokemonNameData['type2'].str.capitalize()
pokemonNameData.fillna('None', inplace = True)

#Järjestetään dataframe käsiteltävään muotoon: pokemonit per numero per maa
pokemonPerCountry = pokemonLocationData.groupby(['country', 'pokemonId']).size()
pokemonPerCountry = pokemonPerCountry.reset_index(name='count')
pokemonPerCountry = pokemonPerCountry.merge(pokemonNameData, left_on = 'pokemonId', right_on = 'pokemonId')
pokemonPerCountry = pokemonPerCountry.sort_values(by=['pokemonId'])

#Bokeh käyttöön
from bokeh.io import show
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, LogColorMapper
from bokeh.palettes import brewer
from bokeh.layouts import row, column
from bokeh.models import ColumnDataSource, CustomJS, TapTool
from bokeh.models.widgets import DataTable, TableColumn

#Spectral6 toimii hyvin koska pokemoneilla on 6 stattia
from bokeh.palettes import Spectral6

#Luodaan datatable pokemoneille per maa
data = dict(pokemonPerCountry)

source = ColumnDataSource(data)
sourceUpdateTable = ColumnDataSource(data=dict())

columns = [
        TableColumn(field='pokemonId', title='Pokemon No.'),
        TableColumn(field='name', title='Name'),
        TableColumn(field='count', title='Count'),
        TableColumn(field='type1', title='Type 1'),
        TableColumn(field='type2', title='Type 2'),
        TableColumn(field='Max HP', title='Max HP'),
        TableColumn(field='Max CP', title='Max CP')
        ]
pokemonCountry = DataTable(source=sourceUpdateTable, columns=columns, width=620, height=300, editable = False, reorderable = False)

#Viedään geodataa Bokehiin
import json

#Viedään geodata jsoniin
merged_json = json.loads(pokemonKartta.to_json())

#Muutetaan tyyppiä
json_data = json.dumps(merged_json)

#Alla kartan piirtäminen, pitäisi toimia
#Geodata jsonista Bokehiin
geosource = GeoJSONDataSource(geojson = json_data)

#Joku paletti käyttöön
palette = brewer['Oranges'][9]

#Tumma = eniten pokemoneja; vaalea = vähiten pokemoneja; harmaa = ei pokemoneja
palette.reverse()

#Lineaarinen color mapping palettiin pokemonien määrän mukaan (myös nan_color mukaan)
color_mapper = LogColorMapper(palette=palette, nan_color = '#d9d9d9')

#Luodaan kaavio
pokemonMap = figure(
   title = 'Pokemon around the world',
   plot_height = 650,
   plot_width = 1000,
   toolbar_location = None,
   tools='tap',
   tooltips=[
      ('Country', '@country'), ('Pokemon sightings', '@count')
   ])

pokemonMap.xgrid.grid_line_color = None
pokemonMap.ygrid.grid_line_color = None
pokemonMap.xaxis.visible = False
pokemonMap.yaxis.visible = False

pokemonMap.hover.point_policy = "follow_mouse"

#Piirretään maat ja väritetään ne
pokemonMap.patches('xs','ys', source = geosource, fill_color = {'field' :'count', 'transform' : color_mapper},
          line_color = 'black', line_width = 0.25, fill_alpha = 1)

#Linkitetään kartta ja datatable
taptool = pokemonMap.select(type=TapTool)
taptool.callback = CustomJS(args=dict(source=source, sourceUpdateTable=sourceUpdateTable), code = """
   var newData = Object.assign({}, source.data)
   sourceUpdateTable.data = newData;
   
   //Luodaan apumuuttujia 
   var newCountry = [];
   var newName = [];
   var newPokemonId = [];
   var newCount = [];
   var newType1 = [];
   var newType2 = [];
   var newMaxHp = [];
   var newMaxCp = [];
   
   //Etsii maan nimen ja tallentaa sen countryName-muuttujaan + tulostaa konsoliin
   var idx = cb_data.source.selected.indices[0];
   var jsonString = cb_data.source.attributes.geojson
   var countryStart = jsonString.split('\"country\"', idx+1).join('\"country\"').length;
   var countryEnd = jsonString.indexOf(",", countryStart);
   var countryName = jsonString.slice(countryStart+12, countryEnd-1);
   
   //Etsitään halutun maan indeksit taulukoista
   var len = sourceUpdateTable.data.country.length;
   var countryIdxArray = [];
   for(var i = 0; i < len; i++) {
      if(sourceUpdateTable.data.country[i] === countryName) {
         countryIdxArray.push(i);
      }
   }
   
   //Sijoitetaan löydettyjen indeksien avulla dataa apumuuttujiin
   for(var j = 0; j < countryIdxArray.length; j++) {
      newCountry.push(sourceUpdateTable.data.country[countryIdxArray[j]]);
      newName.push(sourceUpdateTable.data.name[countryIdxArray[j]]); newPokemonId.push(sourceUpdateTable.data.pokemonId[countryIdxArray[j]]);
      newCount.push(sourceUpdateTable.data.count[countryIdxArray[j]]);
      newType1.push(sourceUpdateTable.data.type1[countryIdxArray[j]]);
      newType2.push(sourceUpdateTable.data.type2[countryIdxArray[j]]);
      newMaxHp.push(sourceUpdateTable.data['Max HP'][countryIdxArray[j]]);
      newMaxCp.push(sourceUpdateTable.data['Max CP'][countryIdxArray[j]]);
   }
   
   //Päivitetään muokattua dataa taulukon lähteeseen
   sourceUpdateTable.data.country = newCountry;
   sourceUpdateTable.data.name = newName;
   sourceUpdateTable.data.pokemonId = newPokemonId;
   sourceUpdateTable.data.count = newCount;
   sourceUpdateTable.data.type1 = newType1;
   sourceUpdateTable.data.type2 = newType2;
   sourceUpdateTable.data['Max HP'] = newMaxHp;
   sourceUpdateTable.data['Max CP'] = newMaxCp;
   
   //Ladataan taulukko uudelleen
   sourceUpdateTable.change.emit();
   """
)

#Kolmas kaavio ja sen linkitys, pokemoninformaatiota palkkeina
pokemonDataStats = pokemonData[['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']]
pokemonDataStatsCol = ColumnDataSource(data=dict(pokemonDataStats))
singlePokemonStats = ColumnDataSource(data=dict(statNames=['Speed', 'Sp. Defense', 'Sp. Attack', 'Defense', 'Attack', 'HP'], statValues=[], color=Spectral6))

#Päivitetään dataa
callback2 = CustomJS(args = dict(sourceUpdateTable = sourceUpdateTable, pokemonDataStatsCol = pokemonDataStatsCol, singlePokemonStats = singlePokemonStats), code = '''
   singlePokemonStats.data.statValues = [];
   
   //Haetaan klikatun pokemonin numero
   row = cb_obj.indices[0]
   selectedId = String(sourceUpdateTable.data['pokemonId'][row]);
      
   //Lisätään oleelliset asiat eteenpäin
   singlePokemonStats.data.statValues.push(pokemonDataStatsCol.data['speed'][selectedId-1]);
   singlePokemonStats.data.statValues.push(pokemonDataStatsCol.data['sp_defense'][selectedId-1]);
   singlePokemonStats.data.statValues.push(pokemonDataStatsCol.data['sp_attack'][selectedId-1]);
   singlePokemonStats.data.statValues.push(pokemonDataStatsCol.data['defense'][selectedId-1]);
   singlePokemonStats.data.statValues.push(pokemonDataStatsCol.data['attack'][selectedId-1]);
   singlePokemonStats.data.statValues.push(pokemonDataStatsCol.data['hp'][selectedId-1]);
   
   singlePokemonStats.change.emit();
''')
sourceUpdateTable.selected.js_on_change('indices', callback2)

statNames = ['Speed', 'Sp. Defense', 'Sp. Attack', 'Defense', 'Attack', 'HP']

#255 on statin maksimi
pokemonView = figure(y_range=statNames, x_range=(0,255), plot_height=320, plot_width=620, title="Main game series stats of selected Pokemon", toolbar_location=None, tools="")
pokemonView.hbar(y='statNames', right='statValues', height=0.9, left=0, color='color', source=singlePokemonStats)
pokemonView.xgrid.grid_line_color = None

#Piirretään kaaviot
show(row(pokemonMap, column(pokemonCountry, pokemonView)))