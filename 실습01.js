function f01(){
  c = document.querySelector("#color01").value
  x = document.querySelector("#target01");
  console.log(x);
  x.style.backgroundColor = c;
}

function f02(num){
  x = document.querySelector("#target02");
  x.style.width = num + 'px';
  x.style.height = num + 'px';
}

function f03(){
  console.log(333);
  input31 = document.querySelector("#input31").value;
  input32 = document.querySelector("#input32").value;
  input33 = document.querySelector("#input33").value;
  resultArea = document.querySelector("#result-area");
  
  s = "구매자:" + input31 + ", 상품명:" + input32 + ", 가격: "+ input33
  resultArea.innerHTML = s;

}