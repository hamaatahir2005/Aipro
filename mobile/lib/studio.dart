import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:image/image.dart' as im;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:pdf/widgets.dart' as pdf;
import 'package:printing/printing.dart';
import 'api.dart';
class DesignLayer {
  String text; Offset position; Color color; double size; Uint8List? image;
  DesignLayer({this.text='TradeMind',this.position=const Offset(30,50),this.color=Colors.white,this.size=32,this.image});
  Map<String,dynamic> json()=>{'text':text,'x':position.dx,'y':position.dy,'color':color.value,'size':size,if(image!=null)'image':base64Encode(image!)};
}
class Studio extends StatefulWidget {
  final Api api; const Studio({super.key,required this.api});
  @override State<Studio> createState()=>_StudioState();
}
class _StudioState extends State<Studio> {
  final canvasKey=GlobalKey();final prompt=TextEditingController();final text=TextEditingController(text:'TradeMind');
  final layers=<DesignLayer>[DesignLayer()]; int selected=0; Color background=const Color(0xff101b2d);String format='Square'; bool busy=false;String? status;
  double get ratio=>format=='Story'?9/16:format=='Poster'?3/4:1;
  Future<void> task(Future<void> Function() fn)async{setState(()=>busy=true);try{await fn();}catch(e){if(mounted)setState(()=>status=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
  Future<Uint8List> capture()async{final boundary=canvasKey.currentContext!.findRenderObject() as RenderRepaintBoundary;final image=await boundary.toImage(pixelRatio:3);final data=await image.toByteData(format:ui.ImageByteFormat.png);image.dispose();return data!.buffer.asUint8List();}
  Future<void> export(String extension)async{final png=await capture();if(extension=='pdf'){final doc=pdf.Document();doc.addPage(pdf.Page(build:(_)=>pdf.Center(child:pdf.Image(pdf.MemoryImage(png)))));await Printing.sharePdf(bytes:await doc.save(),filename:'trademind.pdf');return;}final bytes=extension=='jpg'?im.encodeJpg(im.decodePng(png)!,quality:95):png;final dir=await getTemporaryDirectory();final file=File('${dir.path}/trademind-${DateTime.now().millisecondsSinceEpoch}.$extension');await file.writeAsBytes(bytes);await Share.shareXFiles([XFile(file.path)]);}
  @override void dispose(){prompt.dispose();text.dispose();super.dispose();}
  @override Widget build(BuildContext context)=>ListView(padding:const EdgeInsets.all(18),children:[
    const Text('Graphic Design AI Studio',style:TextStyle(fontSize:24,fontWeight:FontWeight.bold)),
    const Text('Drag layers to position them. Images fill the selected layer using center crop.'),
    if(busy)const LinearProgressIndicator(),if(status!=null)SelectableText(status!),
    DropdownButton<String>(value:format,items:['Square','Story','Poster'].map((v)=>DropdownMenuItem(value:v,child:Text(v))).toList(),onChanged:(v)=>setState(()=>format=v!)),
    Center(child:ConstrainedBox(constraints:const BoxConstraints(maxWidth:400),child:RepaintBoundary(key:canvasKey,child:AspectRatio(aspectRatio:ratio,child:ColoredBox(color:background,child:LayoutBuilder(builder:(context,bounds)=>Stack(clipBehavior:Clip.hardEdge,children:List.generate(layers.length,(i){final l=layers[i];return Positioned(left:l.position.dx,top:l.position.dy,child:GestureDetector(onTap:()=>setState((){selected=i;text.text=l.text;}),onPanUpdate:(d)=>setState(()=>l.position=Offset((l.position.dx+d.delta.dx).clamp(0,bounds.maxWidth-20).toDouble(),(l.position.dy+d.delta.dy).clamp(0,bounds.maxHeight-20).toDouble())),child:l.image==null?Text(l.text,style:TextStyle(fontSize:l.size,color:l.color,fontWeight:FontWeight.bold)):Image.memory(l.image!,width:l.size*5,height:l.size*5,fit:BoxFit.cover)));})))))))),
    Wrap(children:[TextButton(onPressed:()=>setState((){layers.add(DesignLayer(text:'New text'));selected=layers.length-1;text.text='New text';}),child:const Text('Add text')),TextButton(onPressed:()=>task(()async{final file=await ImagePicker().pickImage(source:ImageSource.gallery);if(file!=null){final bytes=await file.readAsBytes();setState((){layers.add(DesignLayer(image:bytes));selected=layers.length-1;});}}),child:const Text('Import image')),TextButton(onPressed:layers.length<=1?null:()=>setState((){layers.removeAt(selected);selected=0;text.text=layers[0].text;}),child:const Text('Delete layer'))]),
    DropdownButton<int>(value:selected,items:List.generate(layers.length,(i)=>DropdownMenuItem(value:i,child:Text('Layer ${i+1} · ${layers[i].image==null?'Text':'Image'}'))),onChanged:(i)=>setState((){selected=i!;text.text=layers[i].text;})),
    TextField(controller:text,onChanged:(v)=>setState(()=>layers[selected].text=v),decoration:const InputDecoration(labelText:'Layer text')),
    Slider(value:layers[selected].size,min:12,max:100,onChanged:(v)=>setState(()=>layers[selected].size=v)),
    Wrap(children:[Colors.white,Colors.black,const Color(0xff45e0c1),const Color(0xff6d55ff),const Color(0xffffcb66)].map((c)=>IconButton(onPressed:()=>setState(()=>layers[selected].color=c),icon:Icon(Icons.circle,color:c))).toList()),
    Wrap(children:[const Color(0xff101b2d),Colors.black,Colors.white,const Color(0xff482a71)].map((c)=>IconButton(onPressed:()=>setState(()=>background=c),icon:Icon(Icons.format_color_fill,color:c))).toList()),
    if(layers[selected].image!=null)Wrap(children:[
      TextButton(onPressed:busy?null:()=>task(()async{final r=await widget.api.call('/design/remove-background',body:{'image_base64':base64Encode(layers[selected].image!)});setState(()=>layers[selected].image=base64Decode(r['image_base64']));}),child:const Text('Remove background')),
      TextButton(onPressed:()=>setState((){final image=im.decodeImage(layers[selected].image!)!;final edge=mathMin(image.width,image.height);layers[selected].image=im.encodePng(im.copyCrop(image,x:(image.width-edge)~/2,y:(image.height-edge)~/2,width:edge,height:edge));}),child:const Text('Center crop square')),
      TextButton(onPressed:()=>setState((){final image=im.decodeImage(layers[selected].image!)!;layers[selected].image=im.encodePng(im.copyResize(image,width:1024));}),child:const Text('Resize to 1024px')),
    ]),
    TextField(controller:prompt,maxLines:3,decoration:const InputDecoration(labelText:'Describe a logo, advertisement, or social design')),
    FilledButton(onPressed:busy?null:()=>task(()async{final result=await widget.api.call('/design/generate',body:{'message':prompt.text});if(result['b64_json']==null)throw Exception('Provider returned no image');setState((){layers.add(DesignLayer(image:base64Decode(result['b64_json'])));selected=layers.length-1;});}),child:const Text('Generate image')),
    OutlinedButton(onPressed:busy?null:()=>task(()async{await widget.api.call('/design/projects',body:{'name':prompt.text,'canvas':{'format':format,'background':background.value,'layers':layers.map((l)=>l.json()).toList()}});setState(()=>status='Project saved');}),child:const Text('Save project')),
    OutlinedButton(onPressed:busy?null:()=>task(()async{final projects=await widget.api.call('/design/projects') as List;if(projects.isEmpty)throw Exception('No saved projects');final p=projects.last['canvas'];setState((){format=p['format'];background=Color(p['background']);layers.clear();for(final l in p['layers']){layers.add(DesignLayer(text:l['text'],position:Offset((l['x'] as num).toDouble(),(l['y'] as num).toDouble()),color:Color(l['color']),size:(l['size'] as num).toDouble(),image:l['image']==null?null:base64Decode(l['image'])));}selected=0;text.text=layers[0].text;});}),child:const Text('Open latest saved project')),
    Wrap(children:['png','jpg','pdf'].map((ext)=>TextButton(onPressed:busy?null:()=>task(()=>export(ext)),child:Text('Export ${ext.toUpperCase()}'))).toList()),
  ]);
}

int mathMin(int a,int b)=>a<b?a:b;
