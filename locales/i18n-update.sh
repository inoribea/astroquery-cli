pybabel extract -F ../babel.cfg -o messages.pot ..

pybabel update -i messages.pot -d .

pybabel compile -d .